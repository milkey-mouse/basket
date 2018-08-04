import sys
import json
import atexit
import numpy as np
import cv2


class NumpyEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        return json.JSONEncoder.default(self, obj)


searchCriteria = (cv2.TERM_CRITERIA_EPS +
                  cv2.TERM_CRITERIA_MAX_ITER, 30, 0.001)
chessboardSize = (7, 7)

objp = np.zeros((chessboardSize[0] * chessboardSize[1], 3), np.float32)
objp[:, :2] = np.mgrid[0:chessboardSize[0],
                       0:chessboardSize[1]].T.reshape(-1, 2)

objPoints = []
imgPoints = []
imgDims = None


def process(img):
    """
        :param img: A numpy array representing the input image
        :returns: A numpy array to send to the mjpg-streamer output plugin
    """
    global imgDims
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    ret, centroids = cv2.findChessboardCorners(gray, chessboardSize, None)
    if ret:
        imgDims = gray.shape[::-1]
        objPoints.append(objp)

        preciseCorners = cv2.cornerSubPix(
            gray, centroids, (3, 3), (-1, -1), searchCriteria)
        imgPoints.append(preciseCorners)

        return cv2.drawChessboardCorners(img, chessboardSize, preciseCorners, True)
    else:
        return img


@atexit.register
def save_calibration_points():
    if len(imgPoints) > 0 and imgDims is not None:
        class NumpyEncoder(json.JSONEncoder):
            def default(self, obj):
                if isinstance(obj, np.ndarray):
                    return obj.tolist()
                return json.JSONEncoder.default(self, obj)

        json.dump({"dimensions": imgDims, "points": imgPoints},
                  sys.stdout, cls=NumpyEncoder, sort_keys=True)
        sys.stdout.flush()
        #ret, mtx, dist, rvecs, tvecs = cv2.calibrateCamera(objPoints, imgPoints, imgDims, None, None)
        #newcameramtx, roi = cv2.getOptimalNewCameraMatrix(mtx, dist, imgDims, 0, imgDims)
        #print(json.dumps(cv2.initUndistortRectifyMap(mtx, dist, None, newcameramtx, imgDims, 5), cls=NumpyEncoder))


def init_filter():
    """
        This function is called after the filter module is imported. It MUST
        return a callable object (such as a function or bound method).
    """
    return process
