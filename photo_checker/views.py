import numpy as np
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
import cv2
from sklearn.cluster import KMeans


class PhotoCheckAPI(APIView):
    parser_classes = (MultiPartParser, FormParser)

    def post(self, request, *args, **kwargs):
        if 'image' not in request.data:
            return Response({'error': 'No image data provided'}, status=400)

        # Process the image
        image = cv2.imdecode(np.fromstring(request.FILES['image'].read(), np.uint8), cv2.IMREAD_UNCHANGED)
        is_white_background = self.has_white_background(image)

        return Response({'is_white_background': is_white_background})

    def has_white_background(self, image, threshold=0.5, num_clusters=2):
        # Perform KMeans clustering to segment the image
        pixels = image.reshape(-1, 3)
        kmeans = KMeans(n_clusters=num_clusters, random_state=0).fit(pixels)
        labels = kmeans.labels_

        # Find the cluster with the most white pixels
        cluster_counts = np.bincount(labels)
        white_cluster = np.argmax(cluster_counts)

        # Calculate the percentage of white pixels in the white cluster
        white_pixel_percentage = np.sum(labels == white_cluster) / len(labels)

        # Check if the percentage exceeds the threshold
        if white_pixel_percentage >= threshold:

            return True
        else:
            return False
