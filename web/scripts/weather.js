/*jshint esversion: 6 */

console.log("JS start");
url=window.location.href;
urli=url.split('/');
station=urli[urli.length - 1];
console.log('station: '+station);

// Initial set of image path:
var weatherImageElement = document.getElementById('weatherImage');
// trick the cache by using random throw-away param ?rand
weatherImageElement.src = '/station/' + station + '?rand=' + Math.random();


setInterval(function() {
    console.log('tick');
    var weatherImageElement = document.getElementById('weatherImage');
    // trick the cache by using random throw-away param ?rand
    weatherImageElement.src = '/station/' + station + '?rand=' + Math.random();
}, 30000);