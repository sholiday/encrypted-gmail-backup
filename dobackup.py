#!/usr/bin/env python
'''
Based on Andrew Jennings' [gmail-backup](https://github.com/abjennings/gmail-backup)
'''

from gmailbackup import GmailBackup

def main():
    gb = GmailBackup()
    gb.run()

if __name__ == '__main__':
    main()
