import numpy as np
import copy
import cv2

from knn_resnet50 import FeatureExtractor

class Card:
    def __init__(self, center_robot, px_size=(224,224),feat_dim=1000):
        self.opened = False
        self.removed = False
        self.image_data = []
        self.features = np.empty((0,feat_dim))
        self.center_robot = center_robot
        self.px_size = px_size
        self.similar_card = None
        self.max_corr = 0.0
        
    def add_image_data(self, crop):
        self.opened = True
        crop = cv2.resize(crop, self.px_size)
        self.image_data.append(crop)

class MemoryState:
    def __init__(self, num_cards, feat_dim=1000):
        self.num_cards = num_cards
        self.cards = []
        self.feat_dim = feat_dim
        self.feature_extractor = FeatureExtractor(feat_dim=self.feat_dim)
    
    def initialize_cards(self, card_centers_robot_xy):
        for j,card_center in enumerate(card_centers_robot_xy):
            if j<self.num_cards:
                self.cards.append(Card(card_center, feat_dim=self.feat_dim))
                                                           
    def update_card_state(self, card, crop):
        card.add_image_data(crop)
        feats = self.feature_extractor.extract(crop)
        card.features = np.vstack((card.features, feats))
        _,max_corr = self.compute_most_similar_card(card)
        print('Maximum Mean Correlation: ', max_corr)
            
    def closest_card(self, card_center_robot, max_dist=30): #mm
        closest_card = None
        smallest_dist = 10000
        for card in self.cards:
            dist = np.linalg.norm(card_center_robot - card.center_robot)
            if dist < smallest_dist and dist < max_dist:
                smallest_dist = dist
                closest_card = card
        print('smallest distance: ', smallest_dist)
        return closest_card
    
    def remove_card_pair(self, card_pair):
        for card in card_pair:
            card.removed = True
            
        for card in self._get_opened_cards():
            if card.similar_card in card_pair:
                card.max_corr = 0.
                self.compute_most_similar_card(card)

    
    def compute_most_similar_card(self, target_card):
        max_corr = 0.
        similar_card = None
        target_features = np.array(target_card.features)
        for card in self._get_opened_cards():
            if card != target_card:
                corr_matrix = np.dot(card.features, target_features.T)
                top4_corrs = np.sort(corr_matrix.reshape(-1))[-4:]
                print(top4_corrs)
                corr = np.mean(top4_corrs)
                if corr > max_corr:
                    max_corr = corr
                    similar_card = card
                if corr > card.max_corr:
                    card.max_corr = corr
                    card.similar_card = target_card
                    
        target_card.max_corr = max_corr
        target_card.similar_card = similar_card
        
        return similar_card, max_corr
                
    def _get_opened_cards(self):
        cards_with_data = []
        for card in self.cards:
            if card.opened and not card.removed:
                cards_with_data.append(card)
        return cards_with_data    
    
    def get_card_image_data(self):
        return [c.image_data[0] for c in self._get_opened_cards()]
    
    def check_for_pairs(self, min_similarity=0.94):
        max_corr = 0.
        next_card = None
        for card in self._get_opened_cards():
            if card.max_corr > max_corr:
                max_corr = card.max_corr
                if max_corr > min_similarity:
                    next_card = card
        return next_card, max_corr
        
if __name__ == '__main__':
    mem_state = MemoryState(6)
    card_centers = np.random.randint(100, size=(6,2))
    mem_state.initialize_cards(card_centers)
    
    query_pos = np.random.randint(100, size=(2))
    query_pos2 = np.random.randint(100, size=(2))
    query_pos3 = np.random.randint(100, size=(2))
    
    closest = mem_state.closest_card(query_pos)
    closest2 = mem_state.closest_card(query_pos2)
    closest3 = mem_state.closest_card(query_pos3)
    
    print(query_pos, closest.center_robot)
    print(query_pos2, closest2.center_robot)
    print(query_pos3, closest3.center_robot)
    
    # query_crop2 = np.random.rand(20,20,3).astype(np.float32)
    query_crop = cv2.imread('/home/msundermeyer/src/mirobot-py/examples/warped_frame_2_32.png')/np.float32(255)
    query_crop2 = cv2.imread('/home/msundermeyer/src/mirobot-py/examples/warped_frame_2_4.png')/np.float32(255)
    query_crop3 = cv2.imread('/home/msundermeyer/src/mirobot-py/examples/warped_frame.png')/np.float32(255)
    
    mem_state.update_card_state(closest,query_crop)
    mem_state.update_card_state(closest2,query_crop2)
    mem_state.update_card_state(closest3,query_crop3)
    
    next, max_corr = mem_state.check_for_pairs()
    print(next.center_robot, max_corr)
    mem_state.remove_card_pair([next, next.similar_card])
    print(closest.similar_card)
    

    
    
                                                               