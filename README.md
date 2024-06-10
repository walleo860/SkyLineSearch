# SkyLineSearch

## Introduction
This projects goal is to create a tool that will allow a user to select an area on a map 
and run a model to show areas within the bounds of that are where it would be possible to rig a highline.  

## How to Contribute
Check out the [Trello Board](https://trello.com/b/kgL4NcVx/to-do)  for current tasks and bugs that need work.  Currently the project has 2 portions:

1) A shiny app for data entry
2) A data pipeline for attribute extraction using Qgis 

What Needs to be Done:

3) Modeling 
4) Using the model pipeline
5) App for said pipeline

## The Shiny App
This app is used for data entry.  As we do not have access to slackmap's database all data has been entered through this app.  The app is very simple and only has the ability to choose if the feature you are entering is riggable or not.  You can then draw a single line on the map to enter data.  If you mess up you can always select the feature you created on the table beneath the map and delete it using the delete button.  Before doing so please verify that it is the feature you think it is. You should be able to open the shiny app by navigating to the server file in Rstudio and clicking "Run App" in the gui.   

## The Data Pipeline - Data Extraction 
The data pipeline is in 2 parts and is set up to run within the Qgis gui. Below is a description of each script.

"01_importing_layers.py" - This script loads all layers that serve as meta data for data extraction.  It also converts the highline csv used in the shiny app into a shapefile.  From this layer, we create a copy of it and turn each line into a series of points 1 meter apart in order to obtain an elevation profile of the ground underneath. DBSCAN clustering is then performed on this layer in order to produce groups of spatial similarity.  This should be monitored as having too large of groups will potentially cause the computer running the 2nd script to crash due to the amount of RAM needed

"02_data_extraction.py" - This script extracts data from other layers and adds information to iether the line's or point line's layer attribute tables. for large vector layers like the United States we can easily extract the locations however for data needed from The National Map API we must itterate through clusters variably.  The while loop itterates through each cluster determined in the importing_layers script. Each itteration does the following:

  1) It creates a bounding box around the cluster's points
  2) Queries The National Map API for 3D elevation maps that contain said bounding box
  3) Determines what other clusters are also within the bounds of the downloaded map
  4) Loops through each of these clusters including the one from step one.
  4a) Creates a bounding bo x for a cluster's points
  4b) Rasterizes a portion of the contour layer downloaded in step 2 with a bounding box created in 4a 
  4c) Extracts the elevation at each point along the line and updates the attribute table
  4d) If a cluster has values for all its points it is added to a vector of clusters to skip and is skipped when the while loop comes to it again
  5) Extracts if the line crosses any railroads, trails, or roads and updates the attribute table
  6) Removes all layers downloaded from The National Map
  7) Deletes all files downloaded from The National Map ( Currently Broken)
  8) Saves layers

## Modeling 
Random forest?

##

