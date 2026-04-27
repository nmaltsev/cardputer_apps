next step:
- Add path traversal protection (../)
- Implement true recursive delete
- Add range requests (partial file streaming)
- Or optimize for Cardputer RAM limits (zero-copy streaming)

TODO fix ui:
1. add link to the parent as ..
2. add icon - directory/file
3. add creation date, modification date
4. add access mode

Issue:
```
NSMaltsev@t13 /cygdrive/c/Users/User/Documents/repos/cardputer_apps/cardputer_webshell
$ ./utils/upload.sh webshell/handlers.py "/usr/webshell/handlers.py"
Uploading webshell/handlers.py -> /usr/webshell/handlers.py
curl: (56) Recv failure: Connection reset by peer
Upload OK
Done
```
