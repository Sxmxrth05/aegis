const { eciToGeodetic, degreesLat, degreesLong, gstime } = require('satellite.js');
const date = new Date('2026-01-14T05:59:30+00:00'); // roughly mid point
const gmst = gstime(date);
const geodetic = eciToGeodetic({ x: -1991.857497525387, y: -4926.160641440504, z: 4224.8089411132605 }, gmst);
console.log('lat:', degreesLat(geodetic.latitude));
console.log('lng:', degreesLong(geodetic.longitude));
