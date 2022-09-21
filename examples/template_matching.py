import cv2
import numpy as np

def multi_scale_template_matching(im1, im2):
    # im1 template, im2 scene

    min_scale = 0.9
    max_scale = 1.0
    num_scales = 10
    canny_low = 60
    canny_high = 150
    verbose = True

    print(im1.dtype, np.min(im1), np.max(im1), im1.shape)
    im1_gray = cv2.cvtColor(im1, cv2.COLOR_BGR2GRAY)
    im1_gray_pad = np.zeros((im1_gray.shape[0]*3//2, im1_gray.shape[1]*3//2),dtype=np.uint8)
    im1_gray_pad[im1_gray.shape[0]//4:im1_gray.shape[0]//4*5,
                   im1_gray.shape[1]//4:im1_gray.shape[1]//4*5] = im1_gray

    im2_gray = cv2.cvtColor(im2, cv2.COLOR_BGR2GRAY)
    im2_gray_canny = cv2.Canny(im2_gray, canny_low, canny_high, apertureSize=3)
    
    tH, tW = im2_gray.shape
    found = None
    for scale in np.linspace(min_scale, max_scale, num_scales)[::-1]:
        resized_im1_gray = cv2.resize(im1_gray_pad, (int(im1_gray_pad.shape[1] * scale),
                                                 int(im1_gray_pad.shape[0] * scale)))
        real_scale = float(im1_gray_pad.shape[0] + im1_gray_pad.shape[1]) / (resized_im1_gray.shape[0] + resized_im1_gray.shape[1])

        resized_im1_gray_canny = cv2.Canny(resized_im1_gray, canny_low, canny_high, apertureSize=3)

        result = cv2.matchTemplate(resized_im1_gray_canny, im2_gray_canny, cv2.TM_CCOEFF_NORMED)

        threshold = 0.25
        loc = np.where( result >= threshold)
        (_, maxVal, _, maxLoc) = cv2.minMaxLoc(result)

        if verbose:
            clone = np.dstack([resized_im1_gray_canny, resized_im1_gray_canny, resized_im1_gray_canny])
            clone_temp = np.dstack([im2_gray_canny, im2_gray_canny, im2_gray_canny])
            result = np.dstack([result, result, result])
            cv2.rectangle(clone, (maxLoc[0], maxLoc[1]),(maxLoc[0] + tW, maxLoc[1] + tH), (0, 0, 255), 2)
            for pt in zip(*loc[::-1]):
                cv2.rectangle(clone, pt, (pt[0] + tW, pt[1] + tH), (255,0,0), 2)
            cv2.imshow("Visualize", clone)
            cv2.imshow("result", result/np.max(result))
            cv2.imshow("template", clone_temp)
            cv2.waitKey(0)
        print("scale {}: {}".format(scale, maxVal))
        # if we have found a new maximum correlation value, then update
        # the bookkeeping variable
        if found is None or maxVal > found[0]:
            found = (maxVal, maxLoc, real_scale)

    # unpack the bookkeeping variable and compute the (x, y) coordinates
    # of the bounding box based on the resized ratio
    (_, maxLoc, real_scale) = found
    (startX, startY) = (int(maxLoc[0] * real_scale - im1_gray.shape[1]//4), 
                        int(maxLoc[1] * real_scale - im1_gray.shape[0]//4))
    (endX, endY) = (int((maxLoc[0] + tW) * real_scale - im1_gray.shape[1]//4), 
                    int((maxLoc[1] + tH) * real_scale - im1_gray.shape[0]//4))
    (X, Y) = (int((maxLoc[0] + tW/2) * real_scale - im1_gray.shape[1]//4),
              int((maxLoc[1] + tH/2) * real_scale - im1_gray.shape[0]//4))

    # draw a bounding box around the detected result and display the image
    # if verbose:
    cv2.rectangle(im1, (startX, startY), (endX, endY), (0, 0, 255), 2)
    cv2.imshow("Image 1", im1)
    cv2.imshow("Image 2", im2)
    cv2.waitKey(0)
    
    return (X, Y, real_scale)

# if __name__ == "__main__":
        
#     #Start capturing images for calibration
#     cap = cv2.VideoCapture(0)
#     cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1600)
#     cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 1200)