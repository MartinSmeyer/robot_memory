# License: BSD
# Author: Sasank Chilamkurthy

from __future__ import print_function, division

import torch
import torch.nn as nn
import torch.optim as optim
from torch.optim import lr_scheduler
import numpy as np
import torchvision
from torchvision import datasets, models, transforms
# import matplotlib.pyplot as plt
import time
import os
import copy
import cv2

class FeatureExtractor():
    
    def __init__(self, feat_dim=1000):
        self.feat_dim = feat_dim

        self.transform = transforms.Compose([
        transforms.ToTensor(),
        transforms.Normalize((0.4914, 0.4822, 0.4465), (0.2023, 0.1994, 0.2010))        
        ])
        model = torchvision.models.resnet50(pretrained=True)
        for param in model.parameters():
            param.requires_grad = False

        device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")
        self.model = model.to(device)
        self.model.eval() 
        
        self.features = np.empty((0,feat_dim))
        
    def extract(self, crop):
        h,w = crop.shape[:2]
        
        crop = cv2.resize(crop, (224,224))
        crops = np.array([crop, np.rot90(crop), np.rot90(crop,2), np.rot90(crop,3)])
        crops = torch.stack([self.transform(c) for c in crops],0)
        print(crops.size())
        feats = self.model(crops.cuda()).cpu().numpy()
        feats /= np.linalg.norm(feats, axis=-1, keepdims=True)
        return feats
    
    # def add_features(self, features):    
    #     self.features = np.vstack((self.features, np.array(features)))
        
    # def knn_correlation(self, features, k=1):
    #     for feat in features:
    #         correlation = np.dot(self.features, feat.reshape(1000,1)/np.linalg.norm(feat)).squeeze()
    #         idx = np.argmax(correlation)
    #     return correlation


    # def predict_class(self, feat):
    #     correlation = np.dot(self.class_templates,feat.reshape(1000,1)/np.linalg.norm(feat)).squeeze()
    #     class_scores = np.mean(correlation,axis=1)
    #     pred = np.argmax(class_scores,axis=0)
    #     return pred



if __name__ == "__main__":

    device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")

    bs = 1
    num_classes = 10
    num_templates = 40
    feat_dim = 1000

    transform = transforms.Compose([
        transforms.Resize(224),
        transforms.ToTensor(),
        transforms.Normalize((0.4914, 0.4822, 0.4465), (0.2023, 0.1994, 0.2010))        
        ])

    trainset = torchvision.datasets.CIFAR10(root='./data', train=True, download=True, transform=transform)
    trainloader = torch.utils.data.DataLoader(trainset, batch_size=bs,shuffle=True, num_workers=4)

    testset = torchvision.datasets.CIFAR10(root='./data', train=False, download=True, transform=transform)
    testloader = torch.utils.data.DataLoader(testset, batch_size=bs, shuffle=True, num_workers=4)




    feature_extractor = FeatureTemplates(num_classes, num_templates, feat_dim)

    samples = 0.
    correct = 0.
    for xb, yb in testloader:
        pred = model(xb.cuda())
        if feature_extractor.check_fullness():
            pred = feature_extractor.predict_class(pred.cpu().numpy().squeeze())
            # print('Predicted: {}    GT: {}'.format(pred, yb.numpy()[0]))
            samples += 1
            if pred == yb.numpy()[0]:
                correct += 1
            print('Acc: {}'.format(correct/samples))
        else:
            feature_extractor.add_template(pred.cpu().numpy().squeeze(), yb.numpy()[0])




