const { eciToGeodetic, degreesLat, degreesLong, gstime } = require('satellite.js');
const date = new Date('2026-01-14T05:29:30+00:00');
const gmst = gstime(date);
const geodetic = eciToGeodetic({ x: -3991.2764754289306, y: 2311.358985709191, z: -4998.831455127059 }, gmst);
console.log('lat:', degreesLat(geodetic.latitude));
console.log('lng:', degreesLong(geodetic.longitude));
