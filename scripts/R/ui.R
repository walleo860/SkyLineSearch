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

ui <- dashboardPage(
  dashboardHeader(
    title = span(
      "Highline Search Data Entry",
      style = "font-size: 16px;"
    ),
    tags$li(
      class = "dropdown",
      tags$span(textOutput("riggable_yes_count"), style = "padding: 0 10px; color: white;")
    ),
    tags$li(
      class = "dropdown",
      tags$span(textOutput("riggable_no_count"), style = "padding: 0 10px; color: white;")
    )
  ),
  dashboardSidebar(
    sidebarMenu(
      menuItem("Map", tabName = "map_tab", icon = icon("map")),
      conditionalPanel(
        condition = "input.show_panels == 'yes'",
        tags$style(type = "text/css", "#zoom, #lat, #lng { display: none; }"),
        sliderInput("zoom", "Zoom Level", min = 1, max = 18, value = 7),
        numericInput("lat", "Latitude", value = 39.5501),
        numericInput("lng", "Longitude", value = -105.7821)
      ),
      radioButtons('riggable', 'Is the line riggable?', c('yes', 'no')),
      radioButtons('show_panels', 'Show Panels?', c('no', 'yes'))
    )
  ),
  dashboardBody(
    fluidRow(
      column(width = 12,
             leafletOutput("map"),
             DTOutput("data_table"),
             actionButton("delete_btn", "Delete Selected Line")
      )
    )
  )
)
