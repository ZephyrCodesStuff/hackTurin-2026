# pip install pandas numpy scikit-learn

import pandas as pd
import numpy as np
from sklearn.cluster import DBSCAN
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import RandomForestClassifier

# 1. Load Data (replace with your actual data)
# Assume 'radar_data.csv' has columns: Frame, Time_s, X_m, Y_m, Velocity_mps, Azimuth_deg
df = pd.read_csv('radar_data.csv')

# --- STAGE 1: CLUSTERING ---
# We cluster frame-by-frame. For demonstration, we'll process a single frame.
frame_data = df[df['Frame'] == 1].copy()

# Select features for clustering (Spatial position + Velocity)
# Velocity is crucial because points moving at the same speed are likely the same object.
cluster_features = frame_data[['X_m', 'Y_m', 'Velocity_mps']]

# Standardize the features (DBSCAN relies on distance metrics)
scaler = StandardScaler()
X_scaled = scaler.fit_transform(cluster_features)

# Apply DBSCAN
# eps: max distance between two samples to be considered in the same neighborhood
# min_samples: number of points required to form a core object
dbscan = DBSCAN(eps=0.5, min_samples=3)
frame_data['Cluster_ID'] = dbscan.fit_predict(X_scaled)

# Filter out noise (DBSCAN assigns -1 to noise/outlier points)
objects_df = frame_data[frame_data['Cluster_ID'] != -1]

# --- STAGE 2: FEATURE EXTRACTION PER CLUSTER ---
# To classify an object, we need aggregate features of the cluster, not individual points.
cluster_features_list = []

for cluster_id, cluster_pts in objects_df.groupby('Cluster_ID'):
    features = {
        'Cluster_ID': cluster_id,
        'Mean_X': cluster_pts['X_m'].mean(),
        'Mean_Y': cluster_pts['Y_m'].mean(),
        'Mean_Velocity': cluster_pts['Velocity_mps'].mean(),
        'Velocity_Spread': cluster_pts['Velocity_mps'].std(), # High for pedestrians (limbs moving), low for cars
        'Spatial_Spread_X': cluster_pts['X_m'].std(),
        'Spatial_Spread_Y': cluster_pts['Y_m'].std(),
        'Point_Count': len(cluster_pts)
    }
    cluster_features_list.append(features)

cluster_df = pd.DataFrame(cluster_features_list).fillna(0)

# --- STAGE 3: CLASSIFICATION ---
# In a real scenario, you would have a labeled dataset to train this model.
# Here is how you structure the Random Forest.

X_classify = cluster_df.drop(columns=['Cluster_ID'])

# Dummy training data setup (Replace with your historically labeled clusters)
X_train = np.random.rand(100, X_classify.shape[1]) 
y_train = np.random.choice(['Pedestrian', 'Car', 'Bicycle'], 100)

clf = RandomForestClassifier(n_estimators=100, random_state=42)
clf.fit(X_train, y_train)

# Predict the objects in our current frame
cluster_df['Predicted_Class'] = clf.predict(X_classify)

print("Detected and Classified Objects:")
print(cluster_df[['Cluster_ID', 'Mean_Velocity', 'Point_Count', 'Predicted_Class']])