import os
import re
import random
import hashlib
import hmac
from string import letters
import string

import webapp2
import jinja2

from google.appengine.ext import db

template_dir = os.path.join(os.path.dirname(__file__), 'templates')
jinja_env = jinja2.Environment(loader = jinja2.FileSystemLoader(template_dir),
                               autoescape = True)

secret = 'helloworld'

def render_str(template, **params):
    t = jinja_env.get_template(template)
    return t.render(params)

# Make User info more secure
def make_secure_val(val):
    return '%s|%s' % (val, hmac.new(secret, val).hexdigest())

# Check if the user info is correct
def check_secure_val(secure_val):
    val = secure_val.split('|')[0]
    if secure_val == make_secure_val(val):
        return val

class BlogHandler(webapp2.RequestHandler):
    def write(self, *a, **kw):
        self.response.out.write(*a, **kw)

    def render_str(self, template, **params):
        params['user'] = self.user
        return render_str(template, **params)

    def render(self, template, **kw):
        self.write(self.render_str(template, **kw))

    def set_secure_cookie(self, name, val):
        cookie_val = make_secure_val(val)
        self.response.headers.add_header(
            'Set-Cookie',
            '%s=%s; Path=/' % (name, cookie_val))

    def read_secure_cookie(self, name):
        cookie_val = self.request.cookies.get(name)
        return cookie_val and check_secure_val(cookie_val)

    def login(self, user):
        self.set_secure_cookie('user_id', str(user.key().id()))

    def logout(self):
        self.response.headers.add_header('Set-Cookie', 'user_id=; Path=/')

    # Every request calls this initialize
    # This function set the user parameter.
    # This allows the blog to know if some user is logged in
    # or none is logged in. If none then it shows "signup" link
    # On the base page.
    def initialize(self, *a, **kw):
        webapp2.RequestHandler.initialize(self, *a, **kw)
        uid = self.read_secure_cookie('user_id')
        self.user = uid and User.by_id(int(uid))

def render_post(response, post):
    response.out.write('<b>' + post.subject + '</b><br>')
    response.out.write(post.content)

##### user stuff
def make_salt(length = 5):
    return ''.join(random.choice(letters) for x in xrange(length))

# Creating Hash for password
def make_pw_hash(name, pw, salt = None):
    if not salt:
        salt = make_salt()
    h = hashlib.sha256(name + pw + salt).hexdigest()
    return '%s,%s' % (salt, h)

# Check the hash pw is same as the original one.
def valid_pw(name, password, h):
    salt = h.split(',')[0]
    return h == make_pw_hash(name, password, salt)

# don't have to do this but this will organize the database
# when you have multiple of them
def users_key(group = 'default'):
    return db.Key.from_path('users', group)

class User(db.Model):
    name = db.StringProperty(required = True)
    pw_hash = db.StringProperty(required = True)
    email = db.StringProperty()

    # This is called a decorater.
    # cls = class -> User not. self the class itself.
    @classmethod
    def by_id(cls, uid):
        return User.get_by_id(uid, parent = users_key())

    @classmethod
    def by_name(cls, name):
        u = User.all().filter('name =', name).get()
        return u

    # Create a new user in User class
    # It's important to use @classmethod because
    # it allows to refer to User class itself
    # instead of a particular instance of User class.
    @classmethod
    def register(cls, name, pw, email = None):
        pw_hash = make_pw_hash(name, pw)
        return User(parent = users_key(),
                    name = name,
                    pw_hash = pw_hash,
                    email = email)

    @classmethod
    def login(cls, name, pw):
        u = cls.by_name(name)
        if u and valid_pw(name, pw, u.pw_hash):
            return u


##### blog stuff

ESSAY_TYPE = {"0": "GRE", "1": "NSF", "2": "SOP"}

def blog_key(name = 'default'):
    return db.Key.from_path('blogs', name)

class Post(db.Model):
    subject = db.StringProperty(required = True)

    prompt = db.TextProperty(required = True)

    content = db.TextProperty(required = True)
    
    created = db.DateTimeProperty(auto_now_add = True)

    username = db.StringProperty(required = True)

    essaytype = db.StringProperty(required = True)

    def render(self):
        self._render_prompt = self.prompt.replace('\n', '<br>')
        self._render_content = self.content.replace('\n', '<br>')
        return render_str("post.html", p = self)

    def render_comments(self, username):
        return render_str("post-comments.html", p = self, username = username)

    def render_prompt(self):
        return self.prompt.replace('\n', '<br>')
    
    # count words
    def count_words(self):
        return len(self.content.split(" "))

    # Essay Type
    def essay_type(self):
        return ESSAY_TYPE[self.essaytype]

    @property
    def comments(self):
        return Comment.all().filter("post = ", str(self.key().id()))

class BlogFront(BlogHandler):
    def get(self):
        if self.user and self.user.name == "wonjunee":
            posts = Post.all().order('-created')
            self.render('front.html', posts = posts)
        else:
            self.redirect('/login')

class GREFront(BlogHandler):
    def get(self):
        if self.user and self.user.name == "wonjunee":
            posts = Post.all().order('-created').filter("essaytype = ", "0")
            self.render('essayfront.html', posts = posts, essaytype = "0", title = "GRE Writings")
        else:
            self.redirect('/login')

class NSFFront(BlogHandler):
    def get(self):
        if self.user and self.user.name == "wonjunee":
            posts = Post.all().order('-created').filter("essaytype = ", "1")
            self.render('essayfront.html', posts = posts, essaytype = "1", title = "NSF Graduate Fellowship")
        else:
            self.redirect('/login')

class SOPFront(BlogHandler):
    def get(self):
        if self.user and self.user.name == "wonjunee":
            posts = Post.all().order('-created').filter("essaytype = ", "2")
            self.render('essayfront.html', posts = posts, essaytype = "2", title = "Statement of Purpose")
        else:
            self.redirect('/login')

class PostPage(BlogHandler):
    def get(self, post_id):
        if self.user and self.user.name == "wonjunee":
            key = db.Key.from_path('Post', int(post_id), parent=blog_key())
            post = db.get(key)

            if not post:
                self.error(404)
                return

            self.render("permalink.html", post = post)
        else:
            self.redirect('/login')

class NewPost(BlogHandler):
    def get(self, essaytype):
        if self.user:
            if self.user.name == "wonjunee":
                self.render("newpost.html")
            else:
                self.redirect("/notallowed0")
        else:
            self.redirect("/login")

    def post(self, essaytype):
        if not self.user:
            self.redirect('/')

        username = self.user.name
        subject = self.request.get('subject')
        prompt = self.request.get('prompt')
        content = self.request.get('content')

        if subject:
            p = Post(parent = blog_key(), 
                subject = subject,
                content = content,
                prompt = prompt,
                username = username,
                essaytype = essaytype)
            p.put()
            self.redirect('/%s' % str(p.key().id()))
        else:
            error = "subject, please!"
            self.render("newpost.html", subject=subject, content=content, username = username,  error=error)

# A class for editing a post
class EditPost(BlogHandler):
    def get(self, post_id):
        key = db.Key.from_path('Post', int(post_id), parent=blog_key())
        post = db.get(key)

        if self.user:
        	if self.user.name == post.username:
	            self.render("editpost.html", subject=post.subject, content=post.content, prompt=post.prompt)
	        else:
	        	self.redirect("/notallowed0")
        else:
            self.redirect("/login")

    def post(self, post_id):
        if not self.user:
            self.redirect('/')

        username = self.user.name
        subject = self.request.get('subject')
        content = self.request.get('content')
        prompt = self.request.get('prompt')
        
        if subject:
            # find a post from the database
            key = db.Key.from_path('Post', int(post_id), parent=blog_key())
            p = db.get(key)

            # Update the post
            p.username = username            
            p.subject = subject
            p.content = content
            p.prompt = prompt
            p.put()

            # Redirect to the single post page with an updated post
            self.redirect('/%s' % str(p.key().id()))

        else:
            error = "subject, please!"
            self.render("newpost.html", subject=subject, content=content, prompt=prompt, username = username,  error=error)

# A class for deleting a post
class DeletePost(BlogHandler):
	def get(self, post_id):
		key = db.Key.from_path('Post', int(post_id), parent=blog_key())
		post = db.get(key)

		if self.user:
			if self.user.name == post.username:
			    self.render("deletepost.html", p = post, subject=post.subject)
			else:
				self.redirect("/notallowed0")
		else:
		    self.redirect("/login")

	def post(self, post_id):
		if not self.user:
			self.redirect('/')

		delete_choice = self.request.get('q')
		username = self.user.name

		if delete_choice == "yes":
			key = db.Key.from_path('Post', int(post_id), parent=blog_key())
			post = db.get(key)
			post.delete()
			self.redirect('/deleted0')
		elif delete_choice == "no":
			self.redirect('/')

USER_RE = re.compile(r"^[a-zA-Z0-9_-]{3,20}$")
def valid_username(username):
    return username and USER_RE.match(username)

PASS_RE = re.compile(r"^.{3,20}$")
def valid_password(password):
    return password and PASS_RE.match(password)

EMAIL_RE  = re.compile(r'^[\S]+@[\S]+\.[\S]+$')
def valid_email(email):
    return not email or EMAIL_RE.match(email)

class Signup(BlogHandler):
    def get(self):
        self.render("signup-form.html")

    def post(self):
        have_error = False
        self.username = self.request.get('username')
        self.password = self.request.get('password')
        self.verify = self.request.get('verify')
        self.email = self.request.get('email')

        params = dict(username = self.username,
                      email = self.email)

        if not valid_username(self.username):
            params['error_username'] = "That's not a valid username."
            have_error = True

        if not valid_password(self.password):
            params['error_password'] = "That wasn't a valid password."
            have_error = True
        elif self.password != self.verify:
            params['error_verify'] = "Your passwords didn't match."
            have_error = True

        if not valid_email(self.email):
            params['error_email'] = "That's not a valid email."
            have_error = True

        if have_error:
            self.render('signup-form.html', **params)
        else:
            self.done()

    def done(self, *a, **kw):
        raise NotImplementedError

class Register(Signup):
    def done(self):
        #make sure the user doesn't already exist
        u = User.by_name(self.username)
        
        if u == None and self.username == "wonjunee":
            # Create a new User instance
            u = User.register(self.username, self.password, self.email)

            # Insert into the database
            u.put()

            # login is from BlogHandler class
            # It creates a secure cookie for a user
            self.login(u)

            # Redirect to the welcome page
            self.redirect('/welcome')
        else:
            msg = 'You are not allowed.'
            self.render('signup-form.html', error_username = msg)

class Login(BlogHandler):
    def get(self):
        self.render('login-form.html')

    def post(self):
        username = self.request.get('username')
        password = self.request.get('password')

        u = User.login(username, password)
        if u and username == "wonjunee":
            self.login(u)
            self.redirect('/')
        else:
            msg = 'Invalid login'
            self.render('login-form.html', error = msg)

class Logout(BlogHandler):
    def get(self):
        self.logout()
        self.redirect('/')

class Welcome(BlogHandler):
    def get(self):
        if self.user:
            self.render('welcome.html', username = self.user.name)
        else:
            self.redirect('/signup')

# DB for comments
class Comment(db.Model):
    post = db.StringProperty(required = True)
    comment = db.TextProperty(required = True)
    created = db.DateTimeProperty(auto_now_add = True)
    username = db.StringProperty(required = True)

    def render(self):
        return self.comment.replace('\n', '<br>')
    def re_render(self):
        return self.comment.replace('<br>','\n')

class NewComment(BlogHandler):
    def get(self,post_id):
        if not self.user:
            return self.redirect("/login")
        post = Post.get_by_id(int(post_id), parent=blog_key())
        subject = post.subject
        self.render(
            "newcomment.html",
            subject=subject,
            pkey=post.key(),
            p = post
            )

    def post(self, post_id):
        if self.user:
            key = db.Key.from_path("Post", int(post_id), parent=blog_key())
            post = db.get(key)
            if not post:
                self.error(404)
                return
            if not self.user:
                return self.redirect("login")
            comment = self.request.get("comment")

            if comment:
                # check how author was defined
                username = self.user.name
                c = Comment(
                    comment=comment,
                    post=post_id,
                    parent=self.user.key(),
                    username=username)
                c.put()
                self.redirect("/%s" % str(post_id))

            else:
                error = "please comment"
                self.render(
                    "newcomment.html",
                    subject=post.subject,
                    pkey=post.key(),
                    p = post,
                    error=error)
        else:
            self.redirect("/login")


# A class for editing a comment
class EditComment(BlogHandler):
    def get(self, post_id, comment_id):
        key = db.Key.from_path('Comment', int(comment_id), parent=self.user.key())
        comment = db.get(key)
        if self.user:
            if not comment:
                self.redirect('/notallowed1')
            else:
                self.render("editcomment.html", comment=comment)
        else:
            self.redirect("/login")

    def post(self, post_id, comment_id):
        if not self.user:
            self.redirect('/')

        usercomment = self.request.get('comment')

        if usercomment:
            key = db.Key.from_path('Comment', int(comment_id), parent=self.user.key())
            comment = db.get(key)
            comment.comment = usercomment
            comment.put()

            self.redirect('/%s' %post_id)
        else:
            error = "comment, please!"
            self.render("editcomment.html", comment=usercomment, error=error)

# A class for deleting a comment
class DeleteComment(BlogHandler):
    def get(self, post_id, comment_id):
        key = db.Key.from_path('Comment', int(comment_id), parent=self.user.key())
        comment = db.get(key)

        if self.user:
            if comment:
                self.render("deletecomment.html", comment=comment)
            else:
                self.redirect("/notallowed1")
        else:
            self.redirect("/login")

    def post(self, post_id, comment_id):
        if not self.user:
            self.redirect('/')

        delete_choice = self.request.get('q')

        if delete_choice == "yes":
            key = db.Key.from_path('Comment', int(comment_id), parent=self.user.key())
            comment = db.get(key)
            comment.delete()
            self.redirect('/deleted1')
        elif delete_choice == "no":
            self.redirect('/')

# This class is for the page that alerts users if
# they attempt to edit posts that are written by others
class NotAllowed(BlogHandler):
    def get(self, post_comment):
        if post_comment == "0":
            post_comment = "Post"
        else:
            post_comment = "Comment"
        self.render('notallowed.html', type=post_comment)

# This class confirms the deletion of posts
class Deleted(BlogHandler):
    def get(self, post_comment):
        if post_comment == "0":
            post_comment = "Post"
        else:
            post_comment = "Comment"
        self.render('deleted.html', post_comment=post_comment)

# A class for summary
class Summary(BlogHandler):
    def get(self):
        if self.user and self.user.name=="wonjunee":
            gres = Post.all().order('-created').filter("essaytype = ", "0")
            nsfs = Post.all().order('-created').filter("essaytype = ", "1")
            sops = Post.all().order('-created').filter("essaytype = ", "2")
            self.render('summary.html', gres=gres, nsfs=nsfs, sops=sops)
        else:
            self.redirect('/login')

app = webapp2.WSGIApplication([
                               ('/?', BlogFront),
                               ('/([0-9]+)', PostPage),
                               ('/gre/?', GREFront),
                               ('/nsf/?', NSFFront),
                               ('/sop/?', SOPFront),
                               ('/newpost([0-9])', NewPost),
                               ('/signup', Register),
                               ('/login', Login),
                               ('/logout', Logout),
                               ('/welcome', Welcome),
                               ('/([0-9]+)/edit', EditPost),
                               ('/([0-9]+)/delete', DeletePost),
                               ('/([0-9]+)/comment/?', NewComment),
                               ('/([0-9]+)/comment/([0-9]+)/edit', EditComment),
                               ('/([0-9]+)/comment/([0-9]+)/delete', DeleteComment),
                               ('/notallowed([0-9])', NotAllowed),
                               ('/deleted([0-9])', Deleted),
                               ('/summary', Summary)
                               ],
                              debug=True)
