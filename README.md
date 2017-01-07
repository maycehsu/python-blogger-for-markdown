# python-blogger-for-markdown

####Purpose: To scan local md files and compare to posts in blogger to create new post or update an existed post based on local md file


Usage:

```
Blogger publish/update.

optional arguments:
  -h, --help        show this help message and exit
  -s, --sync-db     Sync blogger to local db
  -f, --scan-files  scan local files
  -b, --show-db     show posts from db
  -r, --run         run scan files and update/create posts
  -d, --dry-run     dry run to show ready to update/create articles
```

1. run this program to do all process to publish new post or update a post

`python blogger.py -r`

2. dry run only to see what article will be updated or published to blogger

`python blogger.py -d`
