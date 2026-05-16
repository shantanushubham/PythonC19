function fn() {
    // Override with -DbaseUrl=http://... when running against a different environment
    var baseUrl = karate.properties['baseUrl'] || 'http://localhost:8000/api';
    return { baseUrl: baseUrl };
}
