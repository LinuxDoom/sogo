#!/usr/bin/python
from config import hostname, port, username, password, sieve_port, sieve_server

import managesieve
import preferences
import sogotests
import unittest
import utilities
import webdavlib

sieve_simple_vacation="""require ["vacation"];\r\nvacation :days %(days)d :addresses ["%(mailaddr)s"] text:\r\n%(vacation_msg)s\r\n.\r\n;\r\n"""
sieve_vacation_ignoreLists="""require ["vacation"];\r\nif allof ( not exists ["list-help", "list-unsubscribe", "list-subscribe", "list-owner", "list-post", "list-archive", "list-id", "Mailing-List"], not header :comparator "i;ascii-casemap" :is "Precedence" ["list", "bulk", "junk"], not header :comparator "i;ascii-casemap" :matches "To" "Multiple recipients of*" ) {vacation :days %(days)d :addresses ["%(mailaddr)s"] text:\r\n%(vacation_msg)s\r\n.\r\n;\r\n}\r\n"""
sieve_simple_forward="""redirect "%(redirect_mailaddr)s";\r\n"""
sieve_forward_keep="""redirect "%(redirect_mailaddr)s";\r\nkeep;\r\n"""
sieve_simple_filter="""require ["fileinto"];\r\nif anyof (header :contains "subject" "%(subject)s") {\r\n    fileinto "%(folderName)s";\r\n}\r\n"""

class sieveTest(unittest.TestCase):
    def _killFilters(self):
      self.prefs=preferences.preferences()
      # kill existing filters
      self.prefs.set_or_create("SOGoSieveFilters", [], ["defaults"])
      # vacation filters
      self.prefs.set_or_create("autoReplyText", "", ["defaults", "Vacation"])
      self.prefs.set_or_create("autoReplyEmailAddresses", [], ["defaults", "Vacation"])
      self.prefs.set_or_create("daysBetweenResponse", 7, ["defaults", "Vacation"])
      self.prefs.set_or_create("ignoreLists", 0, ["defaults", "Vacation"])
      self.prefs.set_or_create("enabled", 0, ["defaults", "Vacation"])
      # forwarding filters
      self.prefs.set_or_create("forwardAddress", [], ["defaults", "Forward"])
      self.prefs.set_or_create("keepCopy", 0, ["defaults", "Forward"])

    def setUp(self):
      ret = ""

      self.client = webdavlib.WebDAVClient(hostname, port,
                                             username, password)
      utility = utilities.TestUtility(self, self.client)
      (self.user_name, self.user_email) = utility.fetchUserInfo(username)
      self.user_email = self.user_email.replace("mailto:", "")

      self.ms = managesieve.MANAGESIEVE(sieve_server, sieve_port)
      self.assertEqual(self.ms.login("", username, password), "OK",
          "Couldn't login")

      self._killFilters()
	  
    def tearDown(self):
      self._killFilters()

    def _getSogoSieveScript(self):
      sieveFoundsogo=0
      createdSieveScript=""
      (ret, sieveScriptList) = self.ms.listscripts()
      self.assertEqual(ret, "OK", "Couldn't get sieve script list")

      for (script, isActive) in sieveScriptList:
          if (script == "sogo"):
              sieveFoundsogo=1
	      self.assertEqual(isActive, True, "sogo sieve script is not active!")
	      (ret, createdSieveScript) = self.ms.getscript(script)
              self.assertEqual(ret, "OK", "Couldn't get sogo sieve script")

      self.assertEqual(sieveFoundsogo, 1, "sogo sieve script not found!")

      return createdSieveScript

    def testSieveSimpleVacation(self):
      """ enable simple vacation script """
      vacation_msg="vacation test"
      daysSelect=3

      sieveScript = sieve_simple_vacation % { "mailaddr": self.user_email,
                                               "vacation_msg": vacation_msg,
					       "days": preferences.daysBetweenResponseList[daysSelect],
					     }

      # Enabling Vacation now is an 'enabled' setting in the subdict Vacation
      # We need to get that subdict first -- next save/set will also save this
      vacation = self.prefs.get("Vacation")
      vacation['enabled'] = 1

      self.prefs.set_nosave("autoReplyText", vacation_msg)
      self.prefs.set_nosave("daysBetweenResponse", "%d" % preferences.daysBetweenResponseList[daysSelect])
      self.prefs.set_nosave("autoReplyEmailAddresses", [self.user_email])
      self.prefs.save()

      createdSieveScript=self._getSogoSieveScript()

      self.assertEqual(sieveScript, createdSieveScript)
    
    def testSieveVacationIgnoreLists(self):
      """ enable vacation script - ignore lists"""
      vacation_msg="vacation test - ignore list"
      daysSelect=2

      sieveScript = sieve_vacation_ignoreLists % { "mailaddr": self.user_email,
                                               "vacation_msg": vacation_msg,
					       "days": preferences.daysBetweenResponseList[daysSelect],
					     }

      # Enabling Vacation now is an 'enabled' setting in the subdict Vacation
      # We need to get that subdict first -- next save/set will also save this
      vacation = self.prefs.get("Vacation")
      vacation['enabled'] = 1

      self.prefs.set_nosave("autoReplyText", vacation_msg)
      self.prefs.set_nosave("daysBetweenResponse", "%d" % preferences.daysBetweenResponseList[daysSelect])
      self.prefs.set_nosave("autoReplyEmailAddresses", [self.user_email])
      self.prefs.set_nosave("ignoreLists", 1)
      self.prefs.save()

      createdSieveScript=self._getSogoSieveScript()

      self.assertEqual(sieveScript, createdSieveScript)

    def testSieveSimpleForward(self):
      """ enable simple forwarding """
      redirect_mailaddr="nonexistent@inverse.com"

      sieveScript = sieve_simple_forward % { "redirect_mailaddr": redirect_mailaddr }

      # Enabling Forward now is an 'enabled' setting in the subdict Forward
      # We need to get that subdict first -- next save/set will also save this
      forward = self.prefs.get("Forward")
      forward['enabled'] = 1

      self.prefs.set("forwardAddress", [redirect_mailaddr])

      createdSieveScript = self._getSogoSieveScript()
      self.assertEqual(sieveScript, createdSieveScript)

    def testSieveForwardKeepCopy(self):
      """ enable email forwarding - keep a copy """
      redirect_mailaddr="nonexistent@inverse.com"

      sieveScript = sieve_forward_keep % { "redirect_mailaddr": redirect_mailaddr }

      # Enabling Forward now is an 'enabled' setting in the subdict Forward
      # We need to get that subdict first -- next save/set will also save this
      forward = self.prefs.get("Forward")
      forward['enabled'] = 1

      self.prefs.set_nosave("forwardAddress", [redirect_mailaddr])
      self.prefs.set_nosave("keepCopy", 1)
      self.prefs.save()

      createdSieveScript = self._getSogoSieveScript()
      self.assertEqual(sieveScript, createdSieveScript)

    def testSieveSimpleFilter(self):
      """ add simple sieve filter """
      folderName="Sent"
      subject=__name__

      sieveScript=sieve_simple_filter % { "subject": subject, "folderName": folderName }

      self.prefs.set("SOGoSieveFilters", [{"active": True, "actions": [{"method": "fileinto", "argument": "Sent"}], "rules": [{"operator": "contains", "field": "subject", "value": subject}], "match": "any", "name": folderName}])

      createdSieveScript = self._getSogoSieveScript()
      self.assertEqual(sieveScript, createdSieveScript)


if __name__ == "__main__":
    sogotests.runTests()
