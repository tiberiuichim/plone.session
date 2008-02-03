from Products.PageTemplates.PageTemplateFile import PageTemplateFile
from Products.PluggableAuthService.plugins.BasePlugin import BasePlugin
from Products.PluggableAuthService.utils import classImplements
from Products.PluggableAuthService.interfaces.plugins \
        import IExtractionPlugin, IAuthenticationPlugin, \
                ICredentialsResetPlugin, ICredentialsUpdatePlugin
from AccessControl.SecurityInfo import ClassSecurityInfo
from plone.session.interfaces import ISessionPlugin, ISessionSource
import binascii

try:
    from AccessControl.requestmethod import postonly
except ImportError:
    # For Zope <2.8.9, <2.9.7 and <2.10.3
    def postonly(func):
        return func

# Temporary imports
from Products.PluggableAuthService.permissions import ManageUsers


manage_addSessionPluginForm = PageTemplateFile('session', globals())
    

def manage_addSessionPlugin(dispatcher, id, title=None, path='/', REQUEST=None):
    """Add a session plugin."""
    sp=SessionPlugin(id, title=title, path=path)
    dispatcher._setObject(id, sp)

    if REQUEST is not None:
        REQUEST.RESPONSE.redirect('%s/manage_workspace?'
                               'manage_tabs_message=Session+plugin+created.' %
                               dispatcher.absolute_url())



class SessionPlugin(BasePlugin):
    """Session authentication plugin.
    """

    meta_type = "Plone Session Plugin"
    security = ClassSecurityInfo()
    cookie_name = "__ac"

    _properties = (
            {
                "id"    : "title",
                "label" : "Title",
                "type"  : "string",
                "mode"  : "w",
            },
            {
                "id"    : "cookie_name",
                "label" : "Cookie Name root",
                "type"  : "string",
                "mode"  : "w",
            },
            )

    def __init__(self, id, title=None, path="/"):
        self._setId(id)
        self.title=title
        self.path=path

    @property
    def source(self):
        return ISessionSource(self)


    def manage_options(self):
        """Splice in mangae options from our source if it has them."""

        more = getattr(self.source, 'manage_options', ()) 
        if more:
            try:
                more = tuple(more)
            except TypeError:
                more = more()

        return more  + BasePlugin.manage_options


    # ISessionPlugin implementation
    def setupSession(self, userid, response):
        cookie=self.source.createIdentifier(userid)
        cookie=binascii.b2a_base64(cookie).rstrip()

        response.setCookie(self.cookie_name, cookie, path=self.path)


    # IExtractionPlugin implementation
    def extractCredentials(self, request):
        creds={}

        if not self.cookie_name in request:
            return creds

        try:
            creds["cookie"]=binascii.a2b_base64(request.get(self.cookie_name))
        except binascii.Error:
            # If we have a cookie which is not properly base64 encoded it
            # can not be hours.
            return creds

        creds["source"]="plone.session" # XXX should this be the id?

        return creds


    # IAuthenticationPlugin implementation
    def authenticateCredentials(self, credentials):
        if not credentials.get("source", None)=="plone.session":
            return None

        source=self.source
        identifier=credentials["cookie"]
        if source.verifyIdentifier(identifier):
            userid=source.extractUserId(identifier)
            pas=self._getPAS()
            info=pas._verifyUser(pas.plugins, user_id=userid)
            if info is not None:
                return (info['id'], info['login'])

        return None


    # ICredentialsUpdatePlugin implementation
    def updateCredentials(self, request, response, login, new_password):
        pas=self._getPAS()
        info=pas._verifyUser(pas.plugins, login=login)
        if info is not None:
            # Only setup a session for users in our own user folder.
            self.setupSession(info["id"], response)


    # ICredentialsResetPlugin implementation
    def resetCredentials(self, request, response):
        source=self.source

        response=self.REQUEST["RESPONSE"]
        response.expireCookie(self.cookie_name, path=self.path)


classImplements(SessionPlugin, ISessionPlugin,
                IExtractionPlugin, IAuthenticationPlugin,
                ICredentialsResetPlugin, ICredentialsUpdatePlugin)

