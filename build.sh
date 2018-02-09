#! /bin/bash

MODBASE=scripts/client/gui/mods
MODNAME=chirimen.replserver_0.1.1
PKGVERSION=0.1.1

rm -r tmp
mkdir tmp

python2 package.py
cp build/$MODNAME.wotmod tmp

python2 -m compileall client/client.py
mv client/client.pyc tmp

cp LICENSE.txt README.md tmp

( cd tmp; zip -r replserver.zip . )
