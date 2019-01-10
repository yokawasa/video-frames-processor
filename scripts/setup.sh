#!/bin/bash

cwd=`dirname "$0"`
expr "$0" : "/.*" > /dev/null || cwd=`(cd "$cwd" && pwd)`

${cwd}/setup-cosmosdb.sh
${cwd}/setup-word2vecmodel.sh
