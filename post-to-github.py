#coding: utf-8
import workflow, console, keychain, requests, editor
import re, json, base64, time

POSTS_DIR           = '_posts'
BRANCH              = 'master'
GITHUB_USER         = 'lildude'
GITHUB_EMAIL        = 'lildood@gmail.com'
COMMITTER           = {'name': GITHUB_USER, 'email': GITHUB_EMAIL}
GITHUB_TOKEN        = keychain.get_password('RV: GitHub', 'Personal Access Token') # Requires RV: GitHub Authorize workflow to store the token.
GITHUB_REPO         = workflow.get_variable('repo')

content             = editor.get_text()
date                = time.localtime(time.time())
post_tags           = set(['note'])     # Assumes we're a note by default and we don't add other tags to notes.

if len(GITHUB_TOKEN) == 0 or len(GITHUB_REPO) == 0 or len(content) == 0:
	console.hud_alert("Whoops! Token, repository or content is not set.", 'error')
	workflow.stop()

# Determine if this is a post or a note from the content. The clue is if the first
# line starts with a `#`. If so, it's a post, else it's a note.
lines = content.splitlines()

if lines[0].startswith("#"):
    post_type = "post"
    post_title = lines[0].strip('# ')
    commit_msg = "%s - %s" % (post_type, post_title)
    slug = re.sub(r'[-\s]+', '-', re.sub(r'[^\w\s-]', '', post_title).strip().lower())
    # The last line contains the tags in a post
    post_tags = set([re.sub(r"(\W+)$", "", j, flags = re.UNICODE) for j in set([i for i in lines[-1].split() if i.startswith("#")])])
    if lines[-1].startswith('#'): del lines[-1]
    content = "\n".join(lines[1:])
else:
    post_type = "note"
    # Take the first 8 words of the note, strip punctionation and append … if longer
    words = re.findall(r'[^\s!,.?":;]+', content)
    post_title = ' '.join(words[:8])
    if len(words) > 8: post_title += "…"
    slug = str(int(time.strftime('%s', date)) % (24 * 60 * 60))
    commit_msg = "%s - %s" % (post_type, slug)

post_filename = "%s/%s-%s.md" % (POSTS_DIR, time.strftime('%F', date), slug)

# Build frontmatter
frontmatter = "---\nlayout: %s\n" % post_type
if 'post_title' in locals(): frontmatter += "title: \"%s\"\n" % post_title
frontmatter += "date: %s \n" % time.strftime('%F %T %z', date)
if len(post_tags) > 0:
    frontmatter += "tags:\n"
    for t in post_tags: frontmatter += "- %s\n" % t.strip('#')

frontmatter += "type: post\n---\n"

post_content = frontmatter + content

destination_url = "https://%s/%s" % (GITHUB_REPO, slug)

# Post to GitHub - borrowed from https://brightlycolored.org/2016/01/publishing-to-jekyll-from-ios/
URL = 'https://api.github.com/repos/%s/%s/contents/%s' % (GITHUB_USER, GITHUB_REPO, post_filename)

header = {
  'Authorization': 'token %s' % GITHUB_TOKEN,
  'User-Agent': GITHUB_USER
}

get_data = {
  'path': post_filename,
  'ref': BRANCH
}

response = requests.get(URL, headers=header, params=get_data)
response_json = response.json()

if response.status_code == 404:     # File doesn't exist, create it.
  data = {
    'path': post_filename,
    'content': base64.b64encode(post_content),
    'message': "New %s" % commit_msg,
    'branch': BRANCH,
    'committer': COMMITTER
  }

  response = requests.put(URL, headers=header, data=json.dumps(data))

  if response.status_code == 201:
    console.hud_alert("Blog post created successfully.", 'success', 2)
  else:
    console.alert("Commit failed.")
elif response.status_code == 200:   # File exists, update it.
  data = {
    'path': post_filename,
    'content': base64.b64encode(post_content),
    'message': "Updated %s" % commit_msg,
    'branch': BRANCH,
    'committer': COMMITTER,
    'sha': response_json['sha']
  }

  response = requests.put(URL, headers=header, data=json.dumps(data))

  if response.status_code == 200:
    console.hud_alert("Blog post updated successfully.", 'success', 2)
  else:
    console.hud_alert("Commit failed.", 'error')
    workflow.stop()
else:                        # Something went wrong!
  console.hud_alert("There was a problem with the server.", 'error')
  workflow.stop()

# If we get this far, all is great so lets pass on the determined destination URL
workflow.set_output(destination_url)
