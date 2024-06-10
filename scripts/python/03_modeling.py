import numpy as np 
import pandas as pd
import matplotlib.pyplot as plt
plt.style.use('ggplot')
import seaborn as sns
from sklearn import tree
import functions.data_cleaning as dc
import os
import pandas as pd
from sklearn.preprocessing import MinMaxScaler

#path to csvs for analysis
#path = 'Documents/github/highline_search/data/output/'
path = 'data/output/'


lines = pd.read_csv( path + 'highline_anchors.csv')
ele_profiles = pd.read_csv( path + 'highline_anchors_points.csv')

#if data extraction did not conclusivly detect a crossing fill in na
for i in [ 'xsRail', 'xsRoad', 'xsTrail']:
  lines[ i] = lines[ i].fillna( 0)
#factorize categorical variables
lines.home_ancho = pd.factorize( lines.home_ancho)[0]
lines.far_anchor = pd.factorize( lines.far_anchor)[0]
lines.state = pd.factorize( lines.state)[0]

#Create Summary stats for elevation profiles
summary_stats = ele_profiles.groupby('line_id').agg(
    home_elevation=('elevation', 'first'),
    far_elevation=('elevation', 'last'),
    mean_elevation=('elevation', 'mean'),
    median_elevation=('elevation', 'median'),
    min_elevation=('elevation', 'min'),
    max_elevation=('elevation', 'max'),
    std_elevation=('elevation', 'std')
).reset_index()

# Calculate range_elevation separately
summary_stats['range_elevation'] = abs( summary_stats['max_elevation'] - summary_stats['min_elevation'])

#Sag Calculation?
# a 100m long slackline with 15kN tension ( convert to dKn == 1500), that is loaded with a 75kg Slackliner in the middle:
#75 : ((1500 : 100) x 4) = 75 : 60 = approx. 1,25m sag in the middle
#
weight = 60 # kg
length = 100 # m
tension = 1.5 # Kn
sag = (weight / (((tension * 100)/ length)*4))
print( sag)

# Merge summary statistics with anchor elevation difference
lines = pd.merge(lines, summary_stats, on='line_id')

# Add the target variable (usable or not usable)
#df_features = pd.merge(df_features, df_lines[['line_id', 'usable']].drop_duplicates(), on='line_id')


####Plotting elevation profiles####
df_large = pd.merge(lines, ele_profiles, on='line_id')
list( df_large)
df_large['normalized_index'] = df_large.groupby('line_id')['index'].transform(lambda x: x / x.max())

df_riggable_y = df_large[df_large['riggable'] == 1] #yes
df_riggable_n = df_large[df_large['riggable'] == 0] #no

fig, axes = plt.subplots(nrows=1, ncols=2, figsize=(14, 7), sharey=True)

for line_id in df_riggable_y['line_id'].unique():
    subset = df_riggable_y[df_riggable_y['line_id'] == line_id]
    axes[0].plot(subset['normalized_index'], subset['elevation'], marker='o', label=f'line_id {line_id}')

axes[0].set_title('Riggable')
axes[0].set_xlabel('Normalized Line Index')
axes[0].set_ylabel('Elevation')
# Plot for line_ids with riggable == 'n'
for line_id in df_riggable_n['line_id'].unique():
    subset = df_riggable_n[df_riggable_n['line_id'] == line_id]
    axes[1].plot(subset['normalized_index'], subset['elevation'], marker='o', label=f'line_id {line_id}')
axes[1].set_title('Not Riggable')
axes[1].set_xlabel('Normalized Line Index')

# Show the plots
plt.tight_layout()
plt.show()
####

segment_sum = []
for line in ele_profiles.line_id:
    here = ele_profiles[ ele_profiles.line_id == line]    
    seg = dc.split_and_compute_stats( line, here)  
    segment_sum.append( seg)
    


segment_df = pd.concat(segment_sum, ignore_index=True)
line_w_segs = pd.merge(lines, segment_df, on='line_id').drop_duplicates()


line_w_segs['mean_anchor_height'] = 

scaler = MinMaxScaler()

# Select only numeric columns
numeric_cols = line_w_segs.select_dtypes(include=['float']).columns
# Fit and transform the data
line_w_segs[numeric_cols] = scaler.fit_transform( line_w_segs[numeric_cols])

print( line_w_segs.columns)
#Modeling
pcnt = .8

# Random state is a seed value
train = line_w_segs.sample(frac = pcnt, random_state = 20)

test = line_w_segs.drop(train.index)

# Create train and test datasets

X_train = train[['xsRail', 'xsRoad', 'xsTrail',
       'length', 'fs_land', 'blm_land', 'home_elevation', 'far_elevation',
       'mean_elevation', 'median_elevation', 'min_elevation', 'max_elevation',
       'std_elevation', 'range_elevation', '1_mean', '1_median', '1_min',
       '1_max', '1_std', '1_slope', '2_mean', '2_median', '2_min', '2_max',
       '2_std', '2_slope', '3_mean', '3_median', '3_min', '3_max', '3_std',
       '3_slope', '4_mean', '4_median', '4_min', '4_max', '4_std', '4_slope',
       '5_mean', '5_median', '5_min', '5_max', '5_std', '5_slope', '6_mean',
       '6_median', '6_min', '6_max', '6_std', '6_slope', '7_mean', '7_median',
       '7_min', '7_max', '7_std', '7_slope', '8_mean', '8_median', '8_min',
       '8_max', '8_std', '8_slope', '9_mean', '9_median', '9_min', '9_max',
       '9_std', '9_slope', '10_mean', '10_median', '10_min', '10_max',
       '10_std', '10_slope']]

X_test = test[['xsRail', 'xsRoad', 'xsTrail',
       'length', 'fs_land', 'blm_land', 'home_elevation', 'far_elevation',
       'mean_elevation', 'median_elevation', 'min_elevation', 'max_elevation',
       'std_elevation', 'range_elevation', '1_mean', '1_median', '1_min',
       '1_max', '1_std', '1_slope', '2_mean', '2_median', '2_min', '2_max',
       '2_std', '2_slope', '3_mean', '3_median', '3_min', '3_max', '3_std',
       '3_slope', '4_mean', '4_median', '4_min', '4_max', '4_std', '4_slope',
       '5_mean', '5_median', '5_min', '5_max', '5_std', '5_slope', '6_mean',
       '6_median', '6_min', '6_max', '6_std', '6_slope', '7_mean', '7_median',
       '7_min', '7_max', '7_std', '7_slope', '8_mean', '8_median', '8_min',
       '8_max', '8_std', '8_slope', '9_mean', '9_median', '9_min', '9_max',
       '9_std', '9_slope', '10_mean', '10_median', '10_min', '10_max',
       '10_std', '10_slope']]

y_train = train['riggable']

y_test = test['riggable']

np.random.seed(0)


# Creating a decision tree model
clf = tree.DecisionTreeClassifier(criterion = 'entropy', max_depth = 14)

# Fitting the model on the train data
clf = clf.fit(X_train, y_train)

fig, ax = plt.subplots(figsize = (36, 36))

out = tree.plot_tree(clf, fontsize = 10, max_depth = 14, impurity = False, filled = True, feature_names = ['xsRail', 'xsRoad', 'xsTrail',
       'length', 'fs_land', 'blm_land', 'home_elevation', 'far_elevation',
       'mean_elevation', 'median_elevation', 'min_elevation', 'max_elevation',
       'std_elevation', 'range_elevation', '1_mean', '1_median', '1_min',
       '1_max', '1_std', '1_slope', '2_mean', '2_median', '2_min', '2_max',
       '2_std', '2_slope', '3_mean', '3_median', '3_min', '3_max', '3_std',
       '3_slope', '4_mean', '4_median', '4_min', '4_max', '4_std', '4_slope',
       '5_mean', '5_median', '5_min', '5_max', '5_std', '5_slope', '6_mean',
       '6_median', '6_min', '6_max', '6_std', '6_slope', '7_mean', '7_median',
       '7_min', '7_max', '7_std', '7_slope', '8_mean', '8_median', '8_min',
       '8_max', '8_std', '8_slope', '9_mean', '9_median', '9_min', '9_max',
       '9_std', '9_slope', '10_mean', '10_median', '10_min', '10_max',
       '10_std', '10_slope'], class_names = True)

for o in out:

    arrow = o.arrow_patch

    if arrow is not None:

        arrow.set_edgecolor('red')

        arrow.set_linewidth(3)

# Display the plot
plt.show()