from zope.component import queryUtility
from plone.session.sources.base import BaseSource
from plone.keyring.interfaces import IKeyManager
import random, hmac, sha

class NoKeyManager(Exception):
    pass


def GenerateSecret(length=64):
    secret=""
    for i in range(length):
        secret+=chr(random.getrandbits(8))

    return secret


class HashSession(BaseSource):
    """A Hash session source implementation.
    """

    def getSecrets(self):
        manager=queryUtility(IKeyManager, None)
        if manager is None:
            raise NoKeyManager
        return manager[u"_system"]


    def getSigningSecret(self):
        return self.getSecrets()[0]


    def signUserid(self, userid, secret=None):
        if secret is None:
            secret = self.getSigningSecret()

        return hmac.new(secret, userid, sha).hexdigest()


    def createIdentifier(self, userid):
        signature=self.signUserid(userid)

        return "%s %s" % (signature, userid)


    def splitIdentifier(self, identifier):
        index=identifier.rfind(" ")
        if index==-1:
            raise ValueError

        return (identifier[:index], identifier[index+1:])


    def verifyIdentifier(self, identifier):
        try:
            secrets=self.getSecrets()
        except NoKeyManager:
            return False

        for secret in secrets:
            try:
                (signature, userid)=self.splitIdentifier(identifier)
                if  signature==self.signUserid(userid, secret):
# XXX if the secret is not the current signing secret we should reset the cookie
                    return True
            except (AttributeError, ValueError):
                continue

        return False


    def extractUserId(self, identifier):
        (signature, userid)=self.splitIdentifier(identifier)
        return userid


