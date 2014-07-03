import calendar
import ConfigParser
import email
import email.utils
import fcntl
import getpass
import gnupg
import hashlib
import imaplib
import os
import re
import StringIO
import sys
import tarfile

class GmailBackup(object):
    UID_RE = re.compile(r'\d+\s+\(UID (\d+)\)$')
    username = None
    password = None

    def run(self):
        self.config = self.read_config()

        # Ensure only one copy of the script is running per username.
        self.pid_file = self.singleton_lock()

        if self.config.getboolean('backup', 'onexternal') and \
            not os.path.exists(self.config.getboolean('backup', 'path')):
            print 'Drive not mounted. Terminating'
            return

        self.setup_meta_file()
        last_downloaded = self.get_last_downloaded()
        print "Last email downloaded was %d." % last_downloaded

        self.setup_gpg()
        self.setup_tar_file()
        self.setup_imap()

        try:
            # Find the email UID to start downloading.
            start, count = self.find_next_email(last_downloaded)

            for i in xrange(start, count + 1):
                uid = self.get_uid(i)
                print 'Downloading %d/%d (UID: %s)' % (i, count, uid)
                encrypted, timestamp = self.download_message(i)
                self.archive_message(encrypted, timestamp, uid)

                last_downloaded = int(uid)

            self.server.close()

        except KeyboardInterrupt:
            print 'Stopping.'

        finally:
            print 'Cleaning up. Last email downloaded was %d.' % last_downloaded
            self.update_meta_file(last_downloaded)
            self.meta.close()
            self.tar.close()

            
            self.server.logout()


    def read_config(self):
        config = ConfigParser.RawConfigParser()
        found = config.read(os.path.expanduser('~/.encrypted_gmail_backup'))

        # Last step is to check if the user explicitly passed in a config file.
        if len(sys.argv) > 1:
            arg_fname = os.path.expanduser(sys.args[1])
            print 'Using ' + arg_fname
            found += config.read(arg_fname)

        if len(found) == 0:
            print "Could not find any config files."
            print "Try placing one at ~/.encrypted_gmail_backup"
            sys.exit(1)

        self.username = config.get('gmail', 'username')
        self.password = config.get('gmail', 'password')

        return config

    def singleton_lock(self):
        pid_file = None

        if self.config.getboolean('backup', 'use_pid'):
            # Use the hash of the username for the PID.
            # This allows backup of multiple users at the same time.
            username_hash = hashlib.md5(self.username).hexdigest()
            pid_fname = '%s.%s.pid' % (self.config.get('backup', 'pid_prefix'), username_hash)

            pid_file = open(pid_fname, 'w')
            try:
                fcntl.lockf(pid_file, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except IOError:
                print 'Another instance is running for %s, terminating.' % self.username
                sys.exit(0)

        return pid_file

    def setup_meta_file(self):
        fname = self.config.get('backup', 'path') + self.config.get('backup', 'metafile')
        self.meta = None

        if not os.path.isfile(fname):
            print 'Creating meta file ' + fname
            self.meta = open(fname, 'w+')
            self.meta.write('0')
            self.meta.seek(0)

        else:
            self.meta = open(fname, 'r+')

    def get_last_downloaded(self):
        location = int(self.meta.read())
        self.meta.seek(0)
        return location

    def update_meta_file(self, last_downloaded, flush=True):
        self.meta.truncate()
        self.meta.write(str(last_downloaded))
        
        if flush:
            self.meta.flush()

        self.meta.seek(0)


    def setup_tar_file(self):
        fname = self.config.get('backup', 'path') + self.config.get('backup', 'archive')
        self.tar = None

        if not os.path.isfile(fname):
            print 'Creating tar file ' + fname
            self.tar = tarfile.open(name=fname, mode='w:')

        else:
            self.tar = tarfile.open(name=fname, mode='a:')

    def setup_gpg(self):
        binary = self.config.get('gpg', 'binary')
        homedir = os.path.expanduser(self.config.get('gpg', 'home'))

        self.gpg = gnupg.GPG(binary, homedir = homedir)
        self.gpg.encoding = self.config.get('gpg', 'encoding')

    def setup_imap(self):
        print 'Logging in as ' + self.username
        self.server = imaplib.IMAP4_SSL(self.config.get('gmail', 'server'))
        self.server.login(self.username, self.password)

    def find_next_email(self, last_downloaded):
        resp, [countstr] = self.server.select(self.config.get('gmail', 'folder'), True)
        count = int(countstr)

        gotten, ungotten = 0, count + 1
        while (ungotten - gotten) > 1:
            attempt = (gotten + ungotten) / 2
            uid = self.get_uid(attempt)
            if int(uid) <= last_downloaded:
                print 'Finding starting point: %d/%d (UID: %s) too low' % (attempt, count, uid)
                gotten = attempt
            else:
                print 'Finding starting point: %d/%d (UID: %s) too high' % (attempt, count, uid)
                ungotten = attempt

        return (ungotten, count)

    def get_uid(self, n):
        resp, lst = self.server.fetch(n, 'UID')
        m = self.UID_RE.match(lst[0])
        if not m:
            raise Exception('Internal error parsing UID response: %s %s.  Please try again' \
                % (resp, lst))
        return m.group(1)

    def download_message(self, n):
        resp, lst = self.server.fetch(n, '(RFC822)')
        if resp != 'OK':
            raise Exception('Bad response: %s %s' % (resp, lst))

        plaintext = lst[0][1]
        timestamp = self.extract_timestamp(plaintext)
        encrypted = self.gpg.encrypt(plaintext, self.config.get('gpg', 'keyid'), armor=False)

        return [encrypted.data, timestamp]

    def extract_timestamp(self, message):
        msg = email.message_from_string(message)
        date = email.utils.parsedate_tz(msg['Date'])

        timestamp = 0
        
        if date is None:
            pass
        elif date[9] is None:
            # If there was no timezone found, don't adjust the time.
            timestamp = calendar.timegm(date)
        else:
            # We have a valid date, adjust it to UTC.        
            timestamp = calendar.timegm(date) - date[9]

        return timestamp


    def archive_message(self, encrypted, timestamp, uid):
        encrypted_f = StringIO.StringIO()
        encrypted_f.write(encrypted)
        encrypted_f.seek(0)

        info = tarfile.TarInfo(name = uid + '.eml.gpg')
        info.size = len(encrypted_f.buf)
        info.mtime = timestamp
        self.tar.addfile(tarinfo = info, fileobj = encrypted_f)