
/**
 * Corsica Forest Resilience — export Sentinel-2 seasonal medians
 * Exécuter dans https://code.earthengine.google.com/
 * Export Drive → CSV : cell_id, year, season, NDVI, NDMI, n_pixels
 *
 * Prérequis : uploader le GPKG forest_grid_1km (centroïdes) comme asset
 *   assets/USERS/.../corsica_forest_cells
 */
var cells = ee.FeatureCollection('USERS/REPLACE/corsica_forest_cells');
var startYear = 2017;
var endYear = 2025;

function maskS2(img) {
  var scl = img.select('SCL');
  var clear = scl.eq(4).or(scl.eq(5).or(scl.eq(7)));
  return img.updateMask(clear)
    .divide(10000)
    .copyProperties(img, img.propertyNames());
}

function addIndices(img) {
  var ndvi = img.normalizedDifference(['B8', 'B4']).rename('NDVI');
  var ndmi = img.normalizedDifference(['B8', 'B11']).rename('NDMI');
  return img.addBands([ndvi, ndmi]);
}

var seasons = {
  spring: [3, 5],
  summer: [6, 8]
};

var feats = [];
for (var y = startYear; y <= endYear; y++) {
  Object.keys(seasons).forEach(function(season) {
    var m0 = seasons[season][0];
    var m1 = seasons[season][1];
    var start = ee.Date.fromYMD(y, m0, 1);
    var end = ee.Date.fromYMD(y, m1, 1).advance(1, 'month');
    var col = ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED')
      .filterBounds(cells)
      .filterDate(start, end)
      .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 40))
      .map(maskS2)
      .map(addIndices);
    var med = col.select(['NDVI', 'NDMI']).median();
    var reduced = med.reduceRegions({
      collection: cells,
      reducer: ee.Reducer.mean().combine({
        reducer2: ee.Reducer.count(),
        sharedInputs: true
      }),
      scale: 20
    }).map(function(f) {
      return f.set({year: y, season: season});
    });
    feats.push(reduced);
  });
}

var out = ee.FeatureCollection(feats).flatten();
Export.table.toDrive({
  collection: out,
  description: 'corsica_s2_seasonal_ndvi_ndmi',
  fileFormat: 'CSV'
});
