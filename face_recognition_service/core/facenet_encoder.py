from keras_facenet import FaceNet
import numpy as np
import cv2


class FaceNetEncoder:

    def __init__(self):
        self.model = FaceNet()

    def encode(self, face):

        face = cv2.resize(face, (160, 160))

        face = np.expand_dims(face, axis=0)

        embedding = self.model.embeddings(face)

        return embedding[0]