#!/bin/bash

# histogram match all of the component images
for f in georeferenced/*.tif
do
	# histogram match resulting image overwriting original (outupts to null due to future warning)
	echo $f
	rio hist $f georeferenced/East_Africa_50k_18A-3_Yelele.tif $f > /dev/null 2>&1
done

# generate a set of mercator tiles and a leaflet viewer
# gdal2tiles.py -p "mercator" -r "near" -s "EPSG:21906" -z 14 -e -n -w leaflet -t "Uganda" -c "2018 Jonny Huck, #Huckathon" uganda.vrt tiles