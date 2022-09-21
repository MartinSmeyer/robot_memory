#!/usr/bin/env python3
import time
import cv2
import numpy as np
from mirobot import Mirobot

# from webcam_video_stream import WebcamVideoStream

numcards = 2
# filename = '../images/4cards.jpg' 
# longer_card_len_mm = 85 #mm
robot = False

# length of card contour in px 259-290 (for 1600x1200 resolution)



def crop_minAreaRect(img, rect):

    # rotate img
    angle = rect[2]
    rows,cols = img.shape[0], img.shape[1]
    M = cv2.getRotationMatrix2D((cols/2,rows/2),angle,1)
    img_rot = cv2.warpAffine(img,M,(cols,rows))

    # rotate bounding box
    rect0 = (rect[0], rect[1], 0.0) 
    box = cv2.boxPoints(rect0)
    pts = np.int0(cv2.transform(np.array([box]), M))[0]    
    pts[pts < 0] = 0

    # crop
    img_crop = img_rot[pts[1][1]:pts[0][1], 
                       pts[1][0]:pts[2][0]]

    return img_crop

def compute_card_centers(im, numcards = 4, vis=False, threshold=100, white=False):
    im_show = im.copy()
    im_center = np.array(im.shape[::-1])[1:]//2

    # im = cv2.rotate(im, cv2.ROTATE_180)
    # gray = cv2.cvtColor(im,cv2.COLOR_BGR2GRAY)
    
    hsv = cv2.cvtColor(im, cv2.COLOR_BGR2HSV)
    
    if white:
        # mask = cv2.inRange(hsv, (0, 0, 100), (255, 120, 255)) # night
        mask = cv2.inRange(hsv, (0, 0, 200), (255, 25, 255)) # day
        # mask = cv2.inRange(hsv, (0, 0, 110), (255, 110, 255)) # evening
    else:
        mask = cv2.inRange(hsv, (86, 60, 60), (115, 255,255))

    imask = mask>0
    masked_im = np.zeros_like(im, np.uint8)
    masked_im[imask] = im[imask]
    gray = cv2.cvtColor(masked_im, cv2.COLOR_BGR2GRAY)
    if white:
        gray = cv2.GaussianBlur(gray,(3,3), 1000)
    flag, thresh = cv2.threshold(gray, threshold, 255, cv2.THRESH_BINARY)
    # thresh = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 115, 1)
    
    if white:
        cnts, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
        cnt = max(cnts, key=cv2.contourArea)
        # Output
        out = np.zeros(thresh.shape, np.uint8)
        cv2.drawContours(out, [cnt], -1, 255, cv2.FILLED)
        thresh = cv2.bitwise_and(thresh, out)
        
    contours, hierarchy = cv2.findContours(thresh, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
    contours = sorted(contours, key=cv2.contourArea,reverse=True)[:numcards]  

    card_centers_px = []
    boxes_px = []
    img_crops = []
    for card in contours:
        
        x,y,w,h = cv2.boundingRect(card)
        rect_len = 2*w + 2*h
        
        if white:
            rect = cv2.minAreaRect(card)
            box = cv2.boxPoints(rect)
            box = np.int0(box)
            if vis:
                im_show = cv2.drawContours(im_show,[box],0,(0,0,255),2)
        else:
            box = [[x,y], [x+w,y], [x+w,y+h], [x,y+h]]
            
        # careful thresholds depend on camera distance
        # print(rect_len)
        if (rect_len > 229 and rect_len < 300 and not white) or (rect_len > 350 and rect_len < 750 and white):
            boxes_px.append(box)
            card_centers_px.append((x+w//2, y+h//2))
            if white:
                width = int(rect[1][0])
                height = int(rect[1][1])
                src_pts = box.astype("float32")
                dst_pts = np.array([[0, height-1],
                                    [0, 0],
                                    [width-1, 0],
                                    [width-1, height-1]], dtype="float32")
                M = cv2.getPerspectiveTransform(src_pts, dst_pts)
                warped = cv2.warpPerspective(im, M, (width, height))
                
                img_crops.append(warped)
            if vis:
                # cv2.drawContours(im,[box],0,(0,0,255),2)
                im_show = cv2.rectangle(im_show,(x,y),(x+w,y+h),(0,255,0),2)
        elif rect_len >= 300 and not white:
            if 0.8 < w/h < 1.2:
                w_n = int(w / 2)
                h_n = int(h / 2)
                for j in range(2):
                    for i in range(2):
                        x_n  = x + i*w_n
                        y_n  = y + j*h_n
                        boxes_px.append([[x_n,y_n], [x_n+w_n,y_n], [x_n+w_n,y_n+h_n], [x_n,y_n+h_n]])
                        card_centers_px.append((x_n+w_n//2, y_n+h_n//2))
                        if vis:
                            im_show = cv2.rectangle(im_show,(x_n,y_n),(x_n+w_n,y_n+h_n),(255,0,255),2)                
            elif w>h:
                factor = int(np.round(w/h))
                w_n = int(w / factor)
                for i in range(factor):
                    x_n  = x + i*w_n
                    boxes_px.append([[x_n,y], [x_n+w_n,y], [x_n+w_n,y+h], [x_n,y+h]])
                    card_centers_px.append((x_n+w_n//2, y+h//2))
                    if vis:
                        im_show = cv2.rectangle(im_show,(x_n,y),(x_n+w_n,y+h),(255,0,0),2)
            else:
                factor = int(np.round(h/w))
                h_n = int(h / factor)
                for i in range(factor):
                    y_n  = y + i*h_n
                    boxes_px.append([[x,y_n], [x+w,y_n], [x+w,y_n+h_n], [x,y_n+h_n]])
                    card_centers_px.append((x+w//2, y_n+h_n//2))
                    if vis:
                        im_show = cv2.rectangle(im_show,(x,y_n),(x+w,y_n+h_n),(255,0,0),2)
                 
    if vis:
        for card_cent in card_centers_px:
            cv2.circle(im_show,card_cent, 2, (0,0,255), -1)
        # cv2.imshow('img',im) 
        # title = 'white_mask' if white else 'blue_mask'
        # cv2.imshow(title, thresh)
        # cv2.imshow('picked_card', im_show)
        # cv2.waitKey(1)
        return card_centers_px, boxes_px, img_crops, [im_show, thresh] 
        
    return card_centers_px, boxes_px, img_crops


if __name__ == "__main__":
    
    im = cv2.imread('picked_card_screenshot_07.02.2021.png')
    white_card_center,_ = compute_card_centers(im, numcards = 1, vis=True, threshold=40, white=True)
    cv2.imshow('im', im)
    cv2.waitKey(0)

    exit()

    # MirobotCartesians(x=202.0, y=0.0, z=181.0, a=0.0, b=0.0, c=0.0)
    close_gripper = 'M3S1000M4E65'
    open_gripper = 'M3S0M4E40'


    # videoStream = WebcamVideoStream(1,1280,720).start()
    cam = cv2.VideoCapture(0)

    # Default for `wait=` is `True`, but explicitly state it here to showcase this.
    with Mirobot(wait=True, debug=True) as m:
        # Mirobot will by default wait for any command because we specified `wait=True` for the class above.
        m.home_simultaneous()
        upright = [-100, -30, -40]
        m.go_to_axis(*upright)
        mx = 202.00
        my = 0
        mz = 20
        # print our dataclass maintained by Mirobot. Shows the x,y,z,a,b,c coordinates.
        # print(m.cartesian)
        # m.go_to_cartesian_ptp(mx, my, 0)
        # while videoStream.isActive():
        #     image = videoStream.read()
        # m.set_air_pump(0)
        while True:
            ret_val, image = cam.read()

            cv2.imshow('a',image)
            key = cv2.waitKey(1)
            if key == ord('p'):
                cards_mm_to_center = compute_card_centers(image, numcards = numcards, vis=True)
                if robot:
                    for card_pos in cards_mm_to_center:
                        print(card_pos)
                        m.go_to_cartesian_ptp(mx+card_pos[0], my+card_pos[1], 20)
                        m.set_air_pump(1000)
                        m.go_to_cartesian_ptp(mx+card_pos[0], my+card_pos[1], -25)
                        m.go_to_cartesian_ptp(mx+card_pos[0], my+card_pos[1], 20)
                        m.go_to_cartesian_ptp(mx, my, 20)
                        m.set_air_pump(0)

            # # increment arm's position using a for-loop
            


                # print(f"************Count {card_pos}************")

                # # notice how we don't need any "wait" or "sleep" commands!
                # # the following command will only return when the Mirobot returns 'Ok' and when Mirobot is 'Idle'
                # m.go_to_cartesian_ptp(mx, my, 20)

                # m.go_to_cartesian_ptp(mx+card_pos[0], my+card_pos[1], 20)
                # m.set_air_pump(1000)
                # m.go_to_cartesian_ptp(mx+card_pos[0], my+card_pos[1], mz)
                # m.go_to_cartesian_ptp(mx+card_pos[0], my+card_pos[1], 20)
                # m.go_to_cartesian_ptp(mx+card_pos[0], my+card_pos[1], mz)
                # m.set_air_pump(0)
                # m.go_to_cartesian_ptp(mx, my, 20)

                # # print our cartesian coordinates again
                # print(m.cartesian)

