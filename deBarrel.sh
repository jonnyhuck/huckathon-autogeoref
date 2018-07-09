#!/bin/bash

# move into input directory
cd Uganda_50k_Maps

# distort all jpegs in folder
for f in *.jpg
do
	# de-barrel distort and store in new folder
	echo $f
	convert $f -distort barrel "0.008152 -0.009799 0" ../distorted/$f
done

# return to working directory
cd ../