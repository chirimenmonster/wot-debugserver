#! /bin/sh

rm -r tmp

python2 -m compileall -d scripts/client/gui/mods mods

mkdir -p tmp/res/scripts/client/gui/mods/replserver
find mods -name '*.pyc' -exec mv {} tmp/res/scripts/client/gui/{} \;
( cd tmp; zip -0r chirimen.replserver.wotmod res )
rm -r tmp/res

python2 -m compileall client/client.py
mv client/client.pyc tmp

cp LICENSE.txt README.md tmp

( cd tmp; zip -r replserver.zip . )
