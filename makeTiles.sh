#!/bin/bash

# generate a set of mercator tiles and a leaflet viewer
gdal2tiles.py -p "mercator" -r "near" -s "EPSG:21906" -z 14 -e -n -w leaflet -t "Uganda" -c "2018 Jonny Huck, #Huckathon" uganda.vrt tiles