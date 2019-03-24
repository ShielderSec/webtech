#!/usr/bin/env python3
import webtech

# you can use options, same as from the command line
wt = webtech.WebTech(options={'json': True})
report = wt.start_from_url('https://shielder.it')

techs = report['tech']
for tech in techs:
	print(tech)
