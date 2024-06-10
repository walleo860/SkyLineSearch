split_coordinates <- function(coordinates) {
  coords_split <- str_split(coordinates, ", ")
  latitudes <- sapply(coords_split, function(x) as.numeric(x[1]))
  longitudes <- sapply(coords_split, function(x) as.numeric(x[2]))
  return(list(latitude = latitudes, longitude = longitudes))
}