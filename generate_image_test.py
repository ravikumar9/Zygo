"""
Browser Image Verification - Creates HTML report of actual image loading
"""
import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'goexplorer.settings')
django.setup()

from hotels.models import Hotel
from django.conf import settings

# Generate test HTML page
html = f"""
<!DOCTYPE html>
<html>
<head>
    <title>Hotel Image Verification Test</title>
    <style>
        body {{ font-family: Arial; padding: 20px; }}
        .hotel-card {{ 
            border: 1px solid #ddd; 
            padding: 15px; 
            margin-bottom: 20px;
            border-radius: 5px;
        }}
        .hotel-image {{
            max-width: 300px;
            height: 200px;
            object-fit: cover;
            border: 2px solid #28a745;
        }}
        .hotel-image.error {{
            border-color: #dc3545;
        }}
        .status {{
            display: inline-block;
            padding: 5px 10px;
            margin: 5px 0;
            border-radius: 3px;
        }}
        .status.loading {{ background-color: #ffc107; color: #000; }}
        .status.loaded {{ background-color: #28a745; color: #fff; }}
        .status.error {{ background-color: #dc3545; color: #fff; }}
        .url-test {{ 
            background: #f8f9fa; 
            padding: 10px; 
            margin: 10px 0;
            border-left: 4px solid #007bff;
            font-family: monospace;
        }}
    </style>
</head>
<body>
    <h1>🖼️ Hotel Image Verification Test</h1>
    <p><strong>Purpose</strong>: Verify hotel images actually load in browser</p>
    <p><strong>Server</strong>: http://localhost:8000</p>
    <p><strong>Test Date</strong>: {{% now "SHORT_DATETIME_FORMAT" %}}</p>
    
    <hr>
"""

hotels = Hotel.objects.filter(is_active=True).prefetch_related('images')[:5]

for hotel in hotels:
    html += f"""
    <div class="hotel-card">
        <h3>{hotel.name}</h3>
        <p><strong>ID:</strong> {hotel.id}</p>
        <p><strong>display_image_url:</strong> <code>{hotel.display_image_url}</code></p>
        
        <div class="url-test">
            <strong>Direct URL Test:</strong><br>
            <a href="http://localhost:8000{hotel.display_image_url}" target="_blank">
                http://localhost:8000{hotel.display_image_url}
            </a>
        </div>
        
        <p><strong>Image Preview:</strong></p>
        <span class="status loading" id="status-{hotel.id}">⏳ Loading...</span>
        <br><br>
        <img 
            src="{hotel.display_image_url}" 
            alt="{hotel.name}"
            class="hotel-image"
            id="img-{hotel.id}"
            onload="imageLoaded({hotel.id})"
            onerror="imageError({hotel.id})"
        >
        
        <p><strong>Gallery Images:</strong> {hotel.images.count()} total</p>
        <div style="display: flex; gap: 10px; flex-wrap: wrap;">
    """
    
    for idx, img in enumerate(hotel.images.all()[:3]):
        if img.image:
            html += f"""
            <div>
                <img 
                    src="/media/{img.image.name}" 
                    style="width: 100px; height: 100px; object-fit: cover; border: 1px solid #ccc;"
                    alt="Gallery {idx + 1}"
                    title="{img.image.name}"
                >
                <br>
                <small>{'⭐ Primary' if img.is_primary else f'Gallery {idx + 1}'}</small>
            </div>
            """
    
    html += """
        </div>
    </div>
    """

html += """
    <script>
        let loadedCount = 0;
        let errorCount = 0;
        
        function imageLoaded(id) {
            const status = document.getElementById('status-' + id);
            status.textContent = '✅ LOADED';
            status.className = 'status loaded';
            loadedCount++;
            updateSummary();
        }
        
        function imageError(id) {
            const status = document.getElementById('status-' + id);
            status.textContent = '❌ FAILED TO LOAD';
            status.className = 'status error';
            
            const img = document.getElementById('img-' + id);
            img.className = 'hotel-image error';
            errorCount++;
            updateSummary();
        }
        
        function updateSummary() {
            const summary = document.getElementById('summary');
            if (summary) {
                summary.innerHTML = `
                    <strong>Results:</strong> 
                    ✅ Loaded: ${loadedCount} | 
                    ❌ Failed: ${errorCount}
                `;
            }
        }
        
        // Create summary on load
        window.addEventListener('load', function() {
            const body = document.body;
            const summaryDiv = document.createElement('div');
            summaryDiv.id = 'summary';
            summaryDiv.style.cssText = 'position: fixed; top: 10px; right: 10px; padding: 15px; background: white; border: 2px solid #007bff; border-radius: 5px; box-shadow: 0 4px 6px rgba(0,0,0,0.1);';
            body.insertBefore(summaryDiv, body.firstChild);
            
            setTimeout(updateSummary, 2000);
        });
    </script>
</body>
</html>
"""

# Save test file
with open('image_test.html', 'w', encoding='utf-8') as f:
    f.write(html)

print("✅ Test file created: image_test.html")
print("📍 Open this file in your browser to verify image loading")
print(f"   File location: {os.path.abspath('image_test.html')}")
print("\nOR copy to templates and access via Django:")
print("   1. Copy to templates/ directory")
print("   2. Access: http://localhost:8000/static/image_test.html")
