import numpy as np
import cv2
import cv2.aruco as aruco
from tqdm import trange
import datetime

#Start capturing images for calibration
cap = cv2.VideoCapture(1)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1600)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 1200)


#Sets aruco constants
aruco_dict = aruco.Dictionary_get(aruco.DICT_6X6_250)
board = aruco.CharucoBoard_create(5,7,.034,.0203, aruco_dict)
parameters =  aruco.DetectorParameters_create()

#arrays
corners = []
ids = []
rejectedImagePoints = []
charucoCorners = []
charucoIds = []
allCharucoIds = []
allCharucoCorners = []

#calibration output variables
cameraMatrix = None
distCoeffs = None
rvecs = None
tvecs = None
calibrationFlags = 0

print("Aquiring Images For Calibration Move your Camera Around to Capture Different Angles")
for x in trange(40):
    charucoCorners = []
    while len(charucoCorners)<3:
        #read and process image
        ret, frame=cap.read()
        gray = cv2.cvtColor(frame,cv2.COLOR_BGR2GRAY)
        cv2.imshow('frame', gray)
        cv2.waitKey(1)

        #Detect Marker
        corners, ids, rejectedImgPoints = aruco.detectMarkers(gray, aruco_dict, parameters=parameters)
        if len(corners) > 0:
            ret, charucoCorners, charucoIds = aruco.interpolateCornersCharuco(corners, ids, gray, board)
            if charucoCorners is not None and charucoIds is not None and len(charucoCorners)>5:
                allCharucoCorners.append(charucoCorners)
                allCharucoIds.append(charucoIds)
                cv2.waitKey(3000)
                break
            else:
                charucoCorners = []

print("All images Aquired Running Calibration")
print(len(allCharucoCorners))
#release and close
cap.release()
cv2.destroyAllWindows()

imgSize = gray.shape
retval, mtx, dist, rvecs, tvecs = aruco.calibrateCameraCharuco(allCharucoCorners, allCharucoIds, board, imgSize, None, None)
if retval is not None:
    print(mtx)
    np.savez('calibration.npz', ret=retval, mtx=mtx, dist=dist, rvecs=rvecs, tvecs=tvecs)
else:
    print("Sorry there was an issue with your Calibration please try again") 