'''
Extract maps from all files in a directory

The parameters for the barrel distortion are adjusted from the official lens values by trial and error
convert Uganda_50k_Maps/East_Africa_50k_01-4_Zulia.jpg -distort barrel "0.008152 -0.009799 0" distorted/East_Africa_50k_01-4_Zulia_d.jpg

Lens details (from lensfun database):

<distortion model="ptlens" focal="24" a="0.017263" b="-0.049244" c="0"/>
<distortion model="ptlens" focal="28" a="0.010878" b="-0.024454" c="0"/>
<distortion model="ptlens" focal="35" a="0.007152" b="-0.009799" c="0"/>
<distortion model="ptlens" focal="50" a="0.002502" b="0.004803" c="0"/>
<distortion model="ptlens" focal="70" a="0" b="0.009685" c="0"/>
<distortion model="ptlens" focal="88" a="0" b="0.008781" c="0"/>
<distortion model="ptlens" focal="105" a="0" b="0.009598" c="0"/>

This distortion is handled using the deBarrel.sh shell script
'''

import cv2, os, gdal, osr
import numpy as np
from subprocess import call
from pyproj import Proj, transform

def adjustQuadrant(a, b, x, y):
	"""
	* Adjust the x and y values depending upon which quadrant of the grid cell you are in
	"""
	# offset x a quarter of a degree for right two quads
	if b in [2,4]:
		x += 0.25

	# offset y a quarter for a degree for top two quads
	if b in [1,2]:
		y += 0.25
	return x, y

def gridToCoords(a, b):
	"""
	* Convert the Ugandan grid reference to wgs84 coordinates (bottom left corner)
	* returns blx, bly, trx, try
	"""

	# verify inputs are valid (not coprehensive)
	if a < 1 or a > 36 or b < 1 or b > 4:
		raise ValueError('That grid square is not in the database that we are using')
		exit(0)
		
	# The following are odd shapes and need dealing with specially
	if a == 4 and b == 3:
		return 31.0, 3.5, 31.25, 3.8
	elif a == 4 and b == 4:
		return 31.25, 3.5, 31.5, 3.8
	elif a == 5 and b == 3:
		return 31.5, 3.5, 31.75, 3.7666666667
	elif a == 5 and b == 4:
		return 31.75, 3.5, 32.0, 3.8333333333
	elif a == 5 and b == 4:
		return 32.25, 3.5, 32.5, 3.8333333333
	elif a == 10 and b == 4:
		return 34.25, 3.5, 34.5, 3.7833333333
	elif a == 19 and b == 4:
		return 30.7333333333, 2.5, 31, 2.75
	elif a == 28 and b == 2:
		return 30.7166666667, 2.25, 31.0, 2.5
	elif a == 29 and b == 4:
		return 31.1833333333, 2.0, 31.5, 2.25

	# the rest can be calculated based upon their grid position
	else:
		# the following are derived from the map index
		# work out the row and set x and y for the grid cell before adjusting for quadrant
		if a <= 2:
			x = 33.5 + 0.5 * (a-1)
			y = 4.0
			x, y = adjustQuadrant(a, b, x, y)
		elif a <= 10:
			x = 30.5 + 0.5 * (a-3)
			y = 3.5
			x, y = adjustQuadrant(a, b, x, y)
		elif a <= 18:
			x = 30.5 + 0.5 * (a-11)
			y = 3.0
			x, y = adjustQuadrant(a, b, x, y)
		elif a <= 27:
			x = 30.5 + 0.5 * (a-19)
			y = 2.5
			x, y = adjustQuadrant(a, b, x, y)
		elif a <= 36:
			x = 30.5 + 0.5 * (a-28)
			y = 2.0
			x, y = adjustQuadrant(a, b, x, y)
		return x, y, x + 0.25, y + 0.25


# list and loop through all files in directory
for file in os.listdir("distorted/"):

	# only interested in jpgs
    if file.endswith(".jpg"):
		
		print file
		
		# img = cv2.imread('../Full Sheet copy/' + file)
		img = cv2.imread("distorted/" + file)
		orig = img.copy()

		# sharpen the image (weighted subtract gaussian blur from original)
		'''
		https://stackoverflow.com/questions/4993082/how-to-sharpen-an-image-in-opencv
		larger smoothing kernel = more smoothing
		'''
		blur = cv2.GaussianBlur(img, (9,9), 0)
		sharp = cv2.addWeighted(img, 1.5, blur, -0.5, 0)

		# convert the image to grayscale
# 		gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
		gray = cv2.cvtColor(sharp, cv2.COLOR_BGR2GRAY)
		
		# smooth  whilst keeping edges sharp
		'''
		(11) Filter size: Large filters (d > 5) are very slow, so it is recommended to use d=5 for real-time applications, and perhaps d=9 for offline applications that need heavy noise filtering.
		(17, 17) Sigma values: For simplicity, you can set the 2 sigma values to be the same. If they are small (< 10), the filter will not have much effect, whereas if they are large (> 150), they will have a very strong effect, making the image look "cartoonish".
		These values give the best results based upon the sample images
		'''
		gray = cv2.bilateralFilter(gray, 11, 17, 17)
		
		# detect edges
		'''
		(100, 200) Any edges with intensity gradient more than maxVal are sure to be edges and those below minVal are sure to be non-edges, so discarded. Those who lie between these two thresholds are classified edges or non-edges based on their connectivity. If they are connected to "sure-edge" pixels, they are considered to be part of edges.
		'''
		edged = cv2.Canny(gray, 100, 200, apertureSize=3, L2gradient=True)
# 		cv2.imwrite('./edges.jpg', edged)

		# dilate edges to make them more prominent
		kernel = np.ones((3,3),np.uint8)
		edged = cv2.dilate(edged, kernel, iterations=1)
# 		cv2.imwrite('./cvCropped/frame/edges/' + file, edged)

		# find contours in the edged image, keep only the largest ones, and initialize our screen contour
		im2, cnts, hierarchy = cv2.findContours(edged.copy(), cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
		cnts = sorted(cnts, key=cv2.contourArea, reverse=True)[:10]
		screenCnt = None

		# loop over our contours
		for c in cnts:

			# approximate the contour
			peri = cv2.arcLength(c, True)
			approx = cv2.approxPolyDP(c, 0.02 * peri, True)
 
			# if our approximated contour has four points, then we can assume that we have found our screen
			if len(approx) == 4:
				screenCnt = approx
# 				print screenCnt
				cv2.drawContours(img, [screenCnt], -1, (0, 255, 0), 10)
# 				cv2.imwrite('./cvCropped/frame/contours/' + file, img)
				break

		# reshaping contour and initialise output rectangle in top-left, top-right, bottom-right and bottom-left order
		pts = screenCnt.reshape(4, 2)
		rect = np.zeros((4, 2), dtype = "float32")
 
		# the top-left point has the smallest sum whereas the bottom-right has the largest sum
		s = pts.sum(axis = 1)
		rect[0] = pts[np.argmin(s)]
		rect[2] = pts[np.argmax(s)]
 
		# the top-right will have the minumum difference and the bottom-left will have the maximum difference
		diff = np.diff(pts, axis = 1)
		rect[1] = pts[np.argmin(diff)]
		rect[3] = pts[np.argmax(diff)]

		# compute the width and height  of our new image
		(tl, tr, br, bl) = rect
		widthA = np.sqrt(((br[0] - bl[0]) ** 2) + ((br[1] - bl[1]) ** 2))
		widthB = np.sqrt(((tr[0] - tl[0]) ** 2) + ((tr[1] - tl[1]) ** 2))
		heightA = np.sqrt(((tr[0] - br[0]) ** 2) + ((tr[1] - br[1]) ** 2))
		heightB = np.sqrt(((tl[0] - bl[0]) ** 2) + ((tl[1] - bl[1]) ** 2))
 
		# take the maximum of the width and height values to reach our final dimensions
		maxWidth = max(int(widthA), int(widthB))
		maxHeight = max(int(heightA), int(heightB))
 
		# construct our destination points which will be used to map the screen to a top-down, "birds eye" view
		dst = np.array([
			[0, 0],
			[maxWidth - 1, 0],
			[maxWidth - 1, maxHeight - 1],
			[0, maxHeight - 1]], dtype = "float32")
 
		# calculate the perspective transform matrix and warp the perspective to grab the screen
		M = cv2.getPerspectiveTransform(rect, dst)
		warp = cv2.warpPerspective(orig, M, (maxWidth, maxHeight))
		
# 		cv2.imwrite('./cvCropped/frame/' + file, warp)
		
		# crop border off (85px is empirical)
# 		cropBuffer = 85		# this is for the old (phone) images
		cropBuffer = 105	# this is for those taken by Nick
		height, width = warp.shape[:2]
		cropped = warp[cropBuffer:height-cropBuffer, cropBuffer:width-cropBuffer]
		
		# get new image dimensions
		croppedHeight, croppedWidth = cropped.shape[:2]

		# output the result
		cv2.imwrite('./cvCropped/noFrame/' + file, cropped)
		
		# extract grid ref for map from filename and convert to coords
		if file[16:19] == "18A":
			# this is a special case
			blLng, blLat, trLng, trLat = 34.5, 3.0, 34.75, 3.25
		else:
			a = int(file[16:18])
			b = int(file[19:20])
			blLng, blLat, trLng, trLat = gridToCoords(a, b)
		
		# transform to Arc 1960 UTM Zone 36N for each corner of 0.5 degree grid cell
		p1 = Proj(init='epsg:4326')		# WGS84
		p2 = Proj(init='epsg:21096')	# Arc 1960 UTM Zone 36N 
		blX, blY = transform(p1, p2, blLng, blLat)
		tlX, tlY = transform(p1, p2, blLng, trLat)
		trX, trY = transform(p1, p2, trLng, trLat)
		brX, brY = transform(p1, p2, trLng, blLat)
		
# 		print blX, blY
# 		print tlX, tlY
# 		print trX, trY
# 		print brX, brY

		# build list of ground control points
		gcp_list = [
			gdal.GCP(tlX, tlY, 0, 0, 0),
			gdal.GCP(trX, trY, 0, croppedWidth, 0),
			gdal.GCP(brX, brY, 0, croppedWidth, croppedHeight),
			gdal.GCP(blX, blY, 0, 0, croppedHeight),
		]

		# open file with GDAL and write to them
		ds = gdal.Open('./cvCropped/noFrame/' + file) #, gdal.GA_Update)
		
		# Define target SRS using EPSG
		dst_srs = osr.SpatialReference()
		dst_srs.ImportFromEPSG(21096)
		dst_wkt = dst_srs.ExportToWkt()
		
		# apply the wkt's
		ds.SetGCPs(gcp_list, dst_wkt)

		# settings for transform
		error_threshold = 0.125  # error threshold	#same value as in gdalwarp
		resampling = gdal.GRA_NearestNeighbour

		# warp the image to new CRS (effectively does nothing but save the new version)
		tmp_ds = gdal.AutoCreateWarpedVRT( ds,
										   dst_wkt, # None	# src_wkt : left to default value --> will use the one from source
										   dst_wkt,
										   resampling,
										   error_threshold )

		# Create the final warped raster (needs to be GeoTiff for tile creation)
		dst_ds = gdal.GetDriverByName('GTiff').CreateCopy("georeferenced/" + file[:-3]+ "tif", tmp_ds)
		
		# clean up datasets
		dst_ds = None
		tmp_ds = None
		ds = None
		
		
'''
Now all of the sheets are extracted and georeferenced, combine them all into a single VRT
'''
# get all of the files that will be in the vrt
geoFiles = []
for file in os.listdir("georeferenced/"):
	if file.endswith(".tif"):
		geoFiles.append(os.path.join(os.getcwd(), 'georeferenced', file))

# build the vrt - this will be used to convert to tiles
gdal.BuildVRT('uganda.vrt', geoFiles)

# 		break	# for testing