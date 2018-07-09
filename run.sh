#!/bin/bash

# STEP 1
# 
# echo "Removing barrel distortion from images..."
# 
# # move into input directory
# cd Uganda_50k_Maps
# 
# # distort all jpegs in folder
# for f in *.jpg
# do
# 	# de-barrel distort and store in new folder
# 	echo $f
# 	convert $f -distort barrel "0.008152 -0.009799 0" ../distorted/$f > /dev/null 2>&1
# done
# 
# return to working directory
# cd ../
# 
# # STEP 2
# 
# echo "Extracting maps, georeferencing and building VRT..."
# 
# extract and georeference all of the maps and build a VRT
# python findMapInPageBatch.py
# 
# # STEP 3
# 
# echo "Normalising histograms..."
# 
# histogram match all of the component images
# for f in georeferenced/*.tif
# do
# 	histogram match resulting image overwriting original (outupts to null due to future warning)
# 	echo $f
# 	rio hist $f georeferenced/East_Africa_50k_18A-3_Yelele.tif $f > /dev/null 2>&1
# done
# 
## STEP 4

echo "Building tiles..."

# generate a set of mercator tiles and a leaflet viewer
gdal2tiles.py -p "mercator" -r "near" -s "EPSG:21906" -z 14 -e -n -w leaflet -t "Uganda" -c "2018 Jonny Huck, #Huckathon" uganda.vrt tiles

echo "Done!"