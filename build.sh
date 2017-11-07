#! /bin/bash

MODBASE=scripts/client/gui/mods
MODNAME=chirimen.replserver_0.1.0

rm -r tmp

python2 -m compileall -d $MODBASE mods

mkdir -p tmp/res/$MODBASE/replserver
( cd mods; find . -name '*.pyc' -exec mv {} ../tmp/res/$MODBASE/{} \; )
( cd tmp; zip -0r $MODNAME.wotmod res )
rm -r tmp/res

python2 -m compileall client/client.py
mv client/client.pyc tmp

cp LICENSE.txt README.md tmp

( cd tmp; zip -r replserver.zip . )
