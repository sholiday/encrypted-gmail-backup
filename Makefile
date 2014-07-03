clean:
	rm -Rf dist build README EncryptedGmailBackup.egg-info

readme:
	cp README.md README

sdist: clean readme
	python setup.py sdist

post: clean readme
	python setup.py sdist upload