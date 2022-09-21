import numpy as np
import sys
import cv2
import cv2.aruco as aruco
from tqdm import trange
import datetime
import time
from template_matching import multi_scale_template_matching
from segment_cards import compute_card_centers
from pick_card import pick_card, place_card
# from webcam_video_stream import WebcamVideoStream
from video_capture_wo_buffer import VideoCapture
from opencv_utils import stackImages, warpPerspective_numpy,  unproject_px
from memory_state import MemoryState

if len(sys.argv) > 1 and sys.argv[1] == "robot":
    robot = True
else:
    robot = False
    
cap = VideoCapture(-1)
for i in range(10):   
    # Empty buffer
    ret = cap.read()

## Vision parameters
# threshold = 55 # night (gray)
threshold_blue = 40 # medium-high (day)
threshold_white = 50 # medium (day)
numcards = 54

## Set robot world transforms
# world2base_vec = np.array([-0.046, -0.11, 1])
# world2base_vec = np.array([-0.035, -0.1, 1])
# base2world_vec = np.array([0.038,-0.1059, 1])
base2world_vec = np.array([0.0353,-0.1077, 1])
robot_angle = 2.35#2.87534
# base2world = np.array([[np.cos(robot_angle), -np.sin(robot_angle), world2base_vec[0]],
#                         [np.sin(robot_angle), np.cos(robot_angle), world2base_vec[1]],
#                         [0, 0, 1]])
world2base = np.array([[np.cos(robot_angle), np.sin(robot_angle), base2world_vec[0]],
                        [-np.sin(robot_angle), np.cos(robot_angle), base2world_vec[1]],
                        [0, 0, 1]])
base2world = np.linalg.inv(world2base)
world2base_vec = base2world[:,2]

## Load previously saved calibration data
with np.load('calibration.npz') as X:
    camera_matrix, dist_coeffs, rvecs, tvecs = [X[i] for i in ('mtx','dist','rvecs', 'tvecs')]
rvec = rvecs[0]#
tvec = tvecs[0]#np.zeros((3,3))
aruco_dict = aruco.Dictionary_get(aruco.DICT_6X6_250)
board = aruco.CharucoBoard_create(5,7,.034,.0203, aruco_dict)
parameters =  aruco.DetectorParameters_create()

if robot:
    from mirobot import Mirobot
    m = Mirobot(portname='/dev/ttyUSB0', wait=True, debug=True)
    m.home_simultaneous()
    target_x = np.array([292, -45, -9])
    target_r = np.array([0,0,70])
    start_axis = [-64.9, -30, -40, 0, 0, 0]
    out = m.go_to_axis(*start_axis)

# stream = WebcamVideoStream(0, 1600, 1200)
# stream.start()

memory_state = MemoryState(numcards)

img_stack = []

zero = np.zeros((3,3),dtype=np.uint8)
    
while True:
    
    frame = cap.read()
    # cap.update()
    ## undistort (not necessary)
    # h,w = frame.shape[:2]
    # newcameramtx, roi=cv2.getOptimalNewCameraMatrix(camera_matrix,dist_coeffs,(w,h),1,(w,h))
    # frame = cv2.undistort(frame, camera_matrix, dist_coeffs, None, camera_matrix)
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    
    corners, ids, rejectedImgPoints = aruco.detectMarkers(gray, aruco_dict, parameters=parameters)
    if ids is not None:
        ret, charucoCorners, charucoIds = aruco.interpolateCornersCharuco(corners, ids, gray, board)
        
        if( ret > 5 ):
            retval, rvec, tvec = aruco.estimatePoseCharucoBoard(charucoCorners, charucoIds, board, camera_matrix, dist_coeffs, rvec, tvec)
            rmat = cv2.Rodrigues(rvec)[0]

            px_vec = unproject_px(camera_matrix, charucoCorners[0][0], rmat, tvec)

            Hmat =  np.dot(camera_matrix, np.hstack((rmat[:,:2],tvec)))
            Hmat_cv2 = Hmat.dot(np.linalg.inv(camera_matrix))
            Hmat_inv = np.linalg.inv(Hmat)
            Hmat_inv /= Hmat_inv[2,2]
            
            aruco.drawAxis(frame, camera_matrix, dist_coeffs, rvec, tvec, 0.034)
            # aruco.drawAxis(frame, camera_matrix, dist_coeffs, rvec, px_vec, 0.034)
            
            warped_frame = cv2.warpPerspective(frame, Hmat_cv2, (frame.shape[1], frame.shape[0]), flags=cv2.WARP_INVERSE_MAP)
            
            # correct
            card_centers_world_px,_,_,im_show = compute_card_centers(warped_frame, numcards = numcards, white=False, vis=True, threshold=threshold_blue)
            
            card_centers_robot_xy = []
            for card_center in card_centers_world_px:
                card_center_world = np.dot(np.linalg.inv(camera_matrix), np.array([card_center[0], card_center[1], 1]))
                
                # Hack No.1
                if card_center_world[0] < -0.1:
                    card_center_world[0] *= 1.07
                # card_center_base = card_center_world # z-value wrong
                card_center_robot_xy = np.dot(world2base, np.array([card_center_world[0],card_center_world[1], 1]))
                
                card_centers_robot_xy.append(1000 * card_center_robot_xy)  # m to mm
            
            memory_state.initialize_cards(card_centers_robot_xy)
            
            world2base_vec_px = np.dot(camera_matrix, world2base_vec)
            world2base_vec_px /= world2base_vec_px[2]
            
            
            cv2.circle(im_show[0], (int(world2base_vec_px[0]), int(world2base_vec_px[1])), 10, (255,255,0), 6)
            cv2.line(im_show[0], (int(world2base_vec_px[0]), int(world2base_vec_px[1])),
                                    (int(world2base_vec_px[0] + base2world[0,0]*300),
                                     int(world2base_vec_px[1] + base2world[1,0]*300)), (0,0,255), 4)
            cv2.line(im_show[0], (int(world2base_vec_px[0]), int(world2base_vec_px[1])),
                        (int(world2base_vec_px[0] + base2world[0,1]*300),
                            int(world2base_vec_px[1] + base2world[1,1]*300)), (0,255,0), 4)
            
            charuco_worlds = []
            for i,chco in enumerate(charucoCorners):
                charuco_world = np.dot(Hmat_inv, np.array([chco[0][0], chco[0][1], 1]))
                charuco_world /= charuco_world[2]                
                charuco_world_px = np.dot(camera_matrix, charuco_world).astype(np.int32)
                # charuco_world2 = cv2.perspectiveTransform(np.array([chco[0][0], chco[0][1]]).reshape(1,1,2), Hmat_inv).squeeze()
                # charuco_world2_px = np.dot(camera_matrix, np.array([charuco_world2[0], charuco_world2[1],1])).astype(np.int32)
                cv2.circle(frame, tuple(chco[0]), 10, (0,0,int(i/16.*255)), 4)
                cv2.circle(im_show[0], (charuco_world_px[0], charuco_world_px[1]), 10, (0,int(i/16.*255),0), 4)
                # cv2.circle(warped_frame, (charuco_world2_px[0], charuco_world2_px[1]), 10, (int(i/16.*255),0,0), 4)
                charuco_worlds.append(charuco_world)

            cv2.aruco.drawDetectedMarkers(frame,corners,ids)
            img_stack = [[frame, im_show[0], im_show[1], zero], [zero, zero, zero, zero]] 
            stacked_imgs = stackImages(img_stack, 0.7, labels=[])
            cv2.imshow('stacked_imgs', stacked_imgs)
            # cv2.imshow('warped_frame', warped_frame)
            # cv2.imshow('frame', frame)

            if robot:
                if cv2.waitKey(0) & 0xFF == ord('q'):
                    break
            
            for j, card_center_robot in enumerate(card_centers_robot_xy):
            
                next_card, corr = memory_state.check_for_pairs()            
                while next_card is not None:
                    pair = stackImages([[next_card.image_data[0], next_card.similar_card.image_data[0]],[zero,zero]], 1)
                    img_stack[1][3] = pair
                    stacked_imgs = stackImages(img_stack, 0.7, labels=[])
                    cv2.imshow('stacked_imgs', stacked_imgs)
                    cv2.waitKey(0)
                    if robot:
                        for c in [next_card, next_card.similar_card]:
                            ret = pick_card(m, c.center_robot[0], c.center_robot[1]) #robot coords
                            if not ret:
                                print('WARNING: card out of workspace')
                            place_card(m, c.center_robot[0], c.center_robot[1])
                        
                    memory_state.remove_card_pair([next_card, next_card.similar_card])
                    next_card, corr = memory_state.check_for_pairs()               
                
                closest_card = memory_state.closest_card(card_center_robot)
                if closest_card is None or closest_card.opened or closest_card.removed:
                    continue
                
                cv2.circle(im_show[0], card_centers_world_px[j], 10, (0,255,255), 8)
                # cv2.imshow('warped_frame', warped_frame)
                img_stack[0][1] = im_show[0]
                stacked_imgs = stackImages(img_stack, 0.7, labels=[])
                cv2.imshow('stacked_imgs', stacked_imgs)
                cv2.waitKey(0)
                
                if robot:
                    ret = pick_card(m, card_center_robot[0], card_center_robot[1])
                    if not ret:
                        print('WARNING: card out of workspace')
                        continue
                
                while True:
                    for i in range(10):   
                        # Empty buffer
                        ret = cap.read()

                    frame = cap.read()
                    
                    warped_frame2 = cv2.warpPerspective(frame, Hmat_cv2, (frame.shape[1], frame.shape[0]), flags=cv2.WARP_INVERSE_MAP)
                    white_card_center, white_card_box, white_cropped, card_show = compute_card_centers(warped_frame2, numcards = 15, vis=True, 
                                                                                                       threshold=threshold_white, white=True)
                    img_stack[1][0:2] = card_show
                    print(len(white_cropped))
                    # for i,c in enumerate(white_cropped):
                    if white_cropped:
                        memory_state.update_card_state(closest_card, white_cropped[0])
                        img_data= memory_state.get_card_image_data() 
                        root = int(np.ceil(np.sqrt(len(img_data))))
                        revealed_stack = [[img_data[i*root+j] if i*root+j<len(img_data) else zero for j in range(root)] for i in range(root)]
                        img_stack[0][3] = stackImages(revealed_stack, 1)
                        cv2.imshow('stacked_imgs', stacked_imgs)
                    if cv2.waitKey(10) & 0xFF == ord('q'):
                        break
                    if white_cropped and robot:
                        place_card(m, card_center_robot[0], card_center_robot[1])
                        break  
            m.go_to_axis(*start_axis)
        else:
            print('<=5 corners on Charucboard detected')
    # if not robot:
    #     cv2.imshow('frame',frame)
    #     if cv2.waitKey(1) & 0xFF == ord('q'):
    #         break

# When everything done, release the capture
cap.release()
cv2.destroyAllWindows()

