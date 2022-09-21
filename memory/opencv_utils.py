import cv2
import numpy as np
import copy

def stackImages(imgList,scale,labels=[]):
    
    imgArray = copy.deepcopy(imgList)
    
    sizeW= imgArray[0][0].shape[1]
    sizeH = imgArray[0][0].shape[0]
    # imgArray = [imgArray[i:min(i+columns, len(imgArray))] for i in range(0, len(imgArray), columns)]
    rows = len(imgArray)
    cols = len(imgArray[0])
    rowsAvailable = isinstance(imgArray[0], list)
    width = imgArray[0][0].shape[1]
    height = imgArray[0][0].shape[0]
    if rowsAvailable:
        for x in range ( 0, rows):
            for y in range(0, cols):
                imgArray[x][y] = cv2.resize(imgArray[x][y], (int(sizeW * scale), int(sizeH * scale)))
                if len(imgArray[x][y].shape) == 2: imgArray[x][y]= cv2.cvtColor( imgArray[x][y], cv2.COLOR_GRAY2BGR)
        imageBlank = np.zeros((height, width, 3), np.uint8)
        hor = [imageBlank]*rows
        hor_con = [imageBlank]*rows
        for x in range(0, rows):
            hor[x] = np.hstack(imgArray[x])
            hor_con[x] = np.concatenate(imgArray[x])
        ver = np.vstack(hor)
        ver_con = np.concatenate(hor)
    else:
        for x in range(0, rows):
            imgArray[x] = cv2.resize(imgArray[x], (int(sizeW * scale), int(sizeH * scale)))
            if len(imgArray[x].shape) == 2: imgArray[x] = cv2.cvtColor(imgArray[x], cv2.COLOR_GRAY2BGR)
        hor= np.hstack(imgArray)
        hor_con= np.concatenate(imgArray)
        ver = hor
    if len(labels) != 0:
        eachImgWidth= int(ver.shape[1] / cols)
        eachImgHeight = int(ver.shape[0] / rows)
        print(eachImgHeight)
        for d in range(0, rows):
            for c in range (0,cols):
                cv2.rectangle(ver,(c*eachImgWidth,eachImgHeight*d),(c*eachImgWidth+len(labels[d][c])*13+27,30+eachImgHeight*d),(255,255,255),cv2.FILLED)
                cv2.putText(ver,labels[d][c],(eachImgWidth*c+10,eachImgHeight*d+20),cv2.FONT_HERSHEY_COMPLEX,0.7,(255,0,255),2)
    return ver

def unproject_px(camera_matrix, px_coords, rmat, tvec):
    # unproject px coords using camera matrix and reference plane defined by xy of rmat

    # px_ray = c * np.dot(np.linalg.inv(camera_matrix), (px_coords[0], px_coords[1], 1))
    # plane_normal_eq: np.dot(rmat[:,2], (px_ray - tvec)) = 0
    # plane_normal_eq: np.dot(rmat[:,2], (c * np.dot(np.linalg.inv(camera_matrix), (px_coords[0], px_coords[1],1)) - tvec)) = 0
    # np.dot(rmat[:,2], px_ray) = np.dot(rmat[:,2], tvec)

    px_homog = np.dot(np.linalg.inv(camera_matrix), np.array([px_coords[0], px_coords[1], 1]))
    c = np.dot(rmat[:,2], tvec.squeeze()) / np.dot(rmat[:,2], px_homog)
    px_vec = c * px_homog
    return px_vec

def warpPerspective_numpy(frame, Hmat_inv, camera_matrix):
    # difference to cv2.warpPerspective:
    # no interpolation
    # Hmat_inv is in pixel coordinates and not world 

    # could be done offline
    yy,xx = np.meshgrid(np.arange(frame.shape[0]),np.arange(frame.shape[1]))
    coord_list = np.dstack((xx, yy)).reshape(-1,2)
    homog_coord_list = np.hstack((coord_list,np.ones((coord_list.shape[0], 1))))

    color_list = np.transpose(frame, (1,0,2)).reshape(-1,3)

    new_world_coords = np.dot(homog_coord_list, Hmat_inv.T)
    new_world_coords /= new_world_coords[:,2:3]
    new_world_px = np.dot(new_world_coords, camera_matrix.T).astype(np.int32)

    px_in_image = (new_world_px[:,0] >= 0) & (new_world_px[:,0] < frame.shape[1]) & \
                  (new_world_px[:,1] >= 0) & (new_world_px[:,1] < frame.shape[0])
    new_world_px_filtered = new_world_px[px_in_image]

    warped_frame = np.zeros_like(frame)
    warped_frame[new_world_px_filtered[:,1],new_world_px_filtered[:,0], :] = color_list[px_in_image]
    
    # # coord ordering (w,h,3)
    # warped_frame = cv2.transpose(warped_frame)
    
    return warped_frame
