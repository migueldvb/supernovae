#!/usr/local/bin/python3.5

import gzip
import json
import os
from collections import OrderedDict

import ads

from astrocats.catalog.utils import tprint, tq
from astrocats.supernovae.scripts.repos import repo_file_list

sentinel = OrderedDict()

outdir = 'astrocats/supernovae/output/'

path = 'astrocats/supernovae/output/cache/bibauthors.json'
if os.path.isfile(path):
    with open(path, 'r') as f:
        bibauthordict = json.loads(f.read(), object_pairs_hook=OrderedDict)
else:
    bibauthordict = OrderedDict()

files = repo_file_list(bones=False)

path = 'ads.key'
if os.path.isfile(path):
    with open(path, 'r') as f:
        ads.config.token = f.read().splitlines()[0]
else:
    raise IOError(
        "Cannot find ads.key, please generate one at "
        "https://ui.adsabs.harvard.edu/#user/settings/token and place it in "
        "this file.")

for fcnt, eventfile in enumerate(tq(sorted(files, key=lambda s: s.lower()))):
    # if fcnt > 10000:
    #     break
    fileeventname = os.path.splitext(os.path.basename(eventfile))[0].replace(
        '.json', '')

    if eventfile.split('.')[-1] == 'gz':
        with gzip.open(eventfile, 'rt') as f:
            filetext = f.read()
    else:
        with open(eventfile, 'r') as f:
            filetext = f.read()

    item = json.loads(filetext, object_pairs_hook=OrderedDict)
    item = item[list(item.keys())[0]]

    if ('redshift' not in item and
            'claimedtype' not in item) or 'spectra' in item:
        continue

    try:
        qstr = '(full:"' + '" or full:"'.join(
            [x['value'] for x in item['alias']]) + '") '
        allpapers = ads.SearchQuery(
            q=(qstr + ' and property:refereed'),
            fl=['id', 'bibcode', 'author'])
    except:
        continue

    for paper in allpapers:
        bc = paper.bibcode
        if bc not in sentinel:
            allauthors = paper.author
            sentinel[bc] = OrderedDict(
                [('bibcode', bc), ('allauthors', allauthors), ('events', [])])
        sentinel[bc]['events'].append(fileeventname)

    if allpapers:
        rate_limits = allpapers.response.get_ratelimits()
        tprint(fileeventname + '\t(remaining API calls: ' + rate_limits[
            'remaining'] + ')')
        if int(rate_limits['remaining']) <= 10:
            print('ADS API limit reached, terminating early.')
            break

# Convert to array since that's what datatables expects
sentinel = list(sentinel.values())
jsonstring = json.dumps(
    sentinel, indent='\t', separators=(',', ':'), ensure_ascii=False)
with open(outdir + 'sentinel.json', 'w') as f:
    f.write(jsonstring)