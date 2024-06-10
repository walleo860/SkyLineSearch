library(shiny)
library(shinydashboard)
library(ggplot2)
library(leaflet)
library(rsconnect)
library(tidyverse)
library(mapview)
library(sf)
library(sp)
library(leaflet.extras)
library(DT)



server <- function(input, output, session) {
  
  # Path to the CSV file
  csv_file_path <- '../../data/raw/highline_point_data.csv'

  # Reactive value to store the dataframe
  df <- reactiveVal(read.csv(csv_file_path, stringsAsFactors = FALSE))
  
  # Reactive values to store the map's state
  map_state <- reactiveValues(lng = -105.7821, lat = 39.5501, zoom = 7)
  
  # Update map state when the user changes the view
  observeEvent(input$map_zoom, {
    map_state$zoom <- input$map_zoom
  })
  observeEvent(input$map_center, {
    map_state$lng <- input$map_center$lng
    map_state$lat <- input$map_center$lat
  })
  
  summary <- reactive({
    df() %>% 
      group_by(riggable) %>% 
      summarise(count = n()) %>% 
      print()
  })
  
  line_data <- reactive({
    df_data <- df()
    begin <- df_data %>% 
      select(id, home_latitude, home_longitude) %>%
      rename(latitude = home_latitude, longitude = home_longitude)
    
    end <- df_data %>%
      select(id, far_latitude, far_longitude) %>%
      rename(latitude = far_latitude, longitude = far_longitude)
    
    data_lines <- bind_rows(begin, end)
    
    # make data_lines a spatialdataframe
    coordinates(data_lines) <- c('longitude', 'latitude')
    
    # create a list per id
    id_list <- sp::split(data_lines, data_lines[['id']])
    
    id <- 1
    # for each id, create a line that connects all points with that id
    for (i in id_list) {
      event_lines <- SpatialLines(list(Lines(Line(i[1]@coords), ID = id)),
                                  proj4string = CRS("+init=epsg:4326"))
      if (id == 1) {
        sp_lines <- event_lines
      } else {
        sp_lines <- rbind(sp_lines, event_lines)
      }
      id <- id + 1
    }
    return(sp_lines)
  })
  
  output$map <- renderLeaflet({
    leaflet() %>%
      addTiles(
        urlTemplate = "https://basemap.nationalmap.gov/arcgis/rest/services/USGSTopo/MapServer/tile/{z}/{y}/{x}",
        attribution = "Tiles courtesy of the <a href='https://usgs.gov/'>U.S. Geological Survey</a>"
      ) %>%
      setView(lng = map_state$lng, lat = map_state$lat, zoom = map_state$zoom) %>%
      # add dots
      addCircles(data = df(), ~home_longitude, ~home_latitude, 
                 stroke = FALSE, fillOpacity = 0.7) %>%
      addCircles(data = df(), ~far_longitude, ~far_latitude, 
                 stroke = FALSE, fillOpacity = 0.7) %>%
      # add lines
      addPolylines(data = line_data()) %>%
      addDrawToolbar(
        targetGroup = 'draw',
        polylineOptions = drawPolylineOptions(),
        editOptions = editToolbarOptions(edit = TRUE, remove = TRUE)
      ) %>%
      addLayersControl(
        overlayGroups = c('draw'),
        options = layersControlOptions(collapsed = FALSE)
      )
  })
  
  observeEvent(input$map_draw_new_feature, {
    feature <- input$map_draw_new_feature
    if (feature$geometry$type == "LineString") {
      coords <- feature$geometry$coordinates
      if (length(coords) > 2) {
        showNotification("Lines with more than 2 points are not supported.", type = "error")
      } else {
        current_df <- df()
        new_id <- ifelse(nrow(current_df) == 0, 1, max(current_df$id, na.rm = TRUE) + 1)
        new_line <- data.frame(
          id = new_id,
          location = 'unknown',
          home_latitude = coords[[1]][[2]],
          home_longitude = coords[[1]][[1]],
          home_anchor_type = 'unknown',
          far_latitude = coords[[2]][[2]],
          far_longitude = coords[[2]][[1]],
          far_anchor_type = 'unknown',
          riggable = ifelse( input$riggable == 'yes', 1, 0),
          stringsAsFactors = FALSE
        )
        
        updated_df <- bind_rows(current_df, new_line)
        write.csv(updated_df, csv_file_path, row.names = FALSE)
        df(updated_df)  # Update the reactive dataframe
        
        # Reset the map view to the previous state
        leafletProxy("map") %>%
          clearShapes() %>%
          setView(lng = map_state$lng, lat = map_state$lat, zoom = map_state$zoom) %>%
          addCircles(data = updated_df, ~home_longitude, ~home_latitude, 
                     stroke = FALSE, fillOpacity = 0.7) %>%
          addCircles(data = updated_df, ~far_longitude, ~far_latitude, 
                     stroke = FALSE, fillOpacity = 0.7) %>%
          addPolylines(data = line_data())
      }
    }
  })
  
  # Data table output
  output$data_table <- renderDT({
    datatable(df(), selection = 'single')
  })
  
  # Highlight selected line on map
  observeEvent(input$data_table_rows_selected, {
    selected_row <- input$data_table_rows_selected
    if (!is.null(selected_row)) {
      selected_line <- df()[selected_row, ]
      leafletProxy("map") %>%
        clearGroup("highlight") %>%
        addPolylines(
          lng = c(selected_line$home_longitude, selected_line$far_longitude),
          lat = c(selected_line$home_latitude, selected_line$far_latitude),
          color = "red", weight = 5, opacity = 1, group = "highlight"
        )
    }
  })
  
  # Delete selected line
  observeEvent(input$delete_btn, {
    selected_row <- input$data_table_rows_selected
    if (!is.null(selected_row)) {
      updated_df <- df()[-selected_row, ]
      write.csv(updated_df, csv_file_path, row.names = FALSE)
      df(updated_df)
      
      # Update the map
      leafletProxy("map") %>%
        clearShapes() %>%
        setView(lng = map_state$lng, lat = map_state$lat, zoom = map_state$zoom) %>%
        addCircles(data = updated_df, ~home_longitude, ~home_latitude, 
                   stroke = FALSE, fillOpacity = 0.7) %>%
        addCircles(data = updated_df, ~far_longitude, ~far_latitude, 
                   stroke = FALSE, fillOpacity = 0.7) %>%
        addPolylines(data = line_data())
    }
  })
  
  # Reactive outputs for riggable counts
  output$riggable_yes_count <- renderText({
    yes_count <- df() %>% filter(riggable == 'yes') %>% nrow()
    paste("Riggable (Yes):", yes_count)
  })
  
  output$riggable_no_count <- renderText({
    no_count <- df() %>% filter(riggable == 'no') %>% nrow()
    paste("Riggable (No):", no_count)
  })
  
}
