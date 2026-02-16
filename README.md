# Photo Background Checker API

[![Python](https://img.shields.io/badge/Python-3.12-blue.svg)](https://www.python.org/)
[![Django](https://img.shields.io/badge/Django-5.0-green.svg)](https://www.djangoproject.com/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

A production-grade REST API for analyzing photo backgrounds using advanced image processing and machine learning techniques. Built with Django REST Framework and optimized for scalability and performance.

## Features

- **White Background Detection**: Uses K-Means clustering to determine if an image has a white background
- **Batch Processing**: Analyze multiple images in a single request
- **Async Processing**: Background job processing with Celery for large images
- **Detailed Analysis**: Returns confidence scores, dominant colors, and cluster information
- **API Documentation**: Auto-generated OpenAPI/Swagger documentation
- **Production Ready**: Docker, Nginx, Gunicorn, PostgreSQL, Redis support
- **Health Checks**: Built-in health monitoring endpoints
- **Rate Limiting**: Configurable API rate limiting
- **Comprehensive Tests**: Full test coverage with pytest

## Quick Start

### Development Setup

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/photo_background_check.git
   cd photo_background_check
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements/development.txt
   ```

4. **Set up environment variables**
   ```bash
   cp .env.example .env
   # Edit .env with your settings
   ```

5. **Run migrations**
   ```bash
   python manage.py migrate
   ```

6. **Create logs directory**
   ```bash
   mkdir -p logs
   ```

7. **Start development server**
   ```bash
   python manage.py runserver
   ```

8. **Access the API**
   - API: http://localhost:8000/api/v1/
   - Documentation: http://localhost:8000/api/docs/
   - Admin: http://localhost:8000/admin/

### Docker Setup

```bash
# Development
docker-compose -f docker-compose.dev.yml up --build

# Production
docker-compose up --build -d
```

## API Endpoints

### Analyze Photo

```bash
POST /api/v1/analyze/
Content-Type: multipart/form-data

# Parameters:
# - image: Image file (required)
# - threshold: Float 0-1 (optional, default: 0.5)
# - num_clusters: Integer 2-10 (optional, default: 2)
```

**Example Request:**
```bash
curl -X POST http://localhost:8000/api/v1/analyze/ \
  -F "image=@photo.jpg" \
  -F "threshold=0.5"
```

**Example Response:**
```json
{
  "success": true,
  "data": {
    "is_white_background": true,
    "confidence": 0.92,
    "dominant_color": [255, 252, 250],
    "white_pixel_percentage": 0.78,
    "background_type": "white",
    "analysis_details": {
      "cluster_centers": [[255, 252, 250], [45, 45, 48]],
      "cluster_percentages": [0.78, 0.22]
    }
  },
  "processing_time_ms": 145.32
}
```

### Batch Analyze

```bash
POST /api/v1/analyze/batch/
Content-Type: multipart/form-data

# Parameters:
# - images: Multiple image files (required, max 10)
# - threshold: Float 0-1 (optional)
# - async_processing: Boolean (optional)
```

### Photo CRUD Operations

```bash
GET    /api/v1/photos/           # List photos
POST   /api/v1/photos/           # Upload photo
GET    /api/v1/photos/{uuid}/    # Get photo details
DELETE /api/v1/photos/{uuid}/    # Delete photo
POST   /api/v1/photos/{uuid}/analyze/  # Re-analyze photo
```

### Health Check

```bash
GET /health/  # Returns health status of all services
```

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `DJANGO_SECRET_KEY` | Django secret key | Required in production |
| `DJANGO_DEBUG` | Enable debug mode | `False` |
| `DJANGO_ALLOWED_HOSTS` | Comma-separated hosts | `localhost,127.0.0.1` |
| `DJANGO_ENVIRONMENT` | `development`, `staging`, `production` | `development` |
| `DATABASE_URL` | Database connection URL | SQLite in development |
| `REDIS_URL` | Redis connection URL | `redis://localhost:6379/0` |
| `CELERY_BROKER_URL` | Celery broker URL | `redis://localhost:6379/1` |
| `RATE_LIMIT_ANON` | Anonymous rate limit | `100/hour` |
| `RATE_LIMIT_USER` | Authenticated rate limit | `1000/hour` |
| `MAX_UPLOAD_SIZE_MB` | Max upload size | `10` |

### Image Processing Settings

Configure in `settings/base.py`:

```python
IMAGE_PROCESSING = {
    'DEFAULT_WHITE_THRESHOLD': 0.5,
    'DEFAULT_NUM_CLUSTERS': 2,
    'MAX_IMAGE_DIMENSION': 4096,
    'WHITE_COLOR_THRESHOLD': 240,
    'PROCESSING_TIMEOUT': 60,
}
```

## Architecture

```
photo_background_check/
├── photo_background_check/     # Project configuration
│   ├── settings/               # Split settings (base/dev/prod)
│   ├── celery.py              # Celery configuration
│   └── urls.py                # Root URL routing
├── photo_checker/              # Main application
│   ├── models.py              # Database models
│   ├── views.py               # API views
│   ├── serializers.py         # DRF serializers
│   ├── services/              # Image processing service
│   ├── tasks.py               # Celery tasks
│   ├── utils/                 # Utilities (logging, exceptions)
│   └── tests/                 # Test suite
├── nginx/                      # Nginx configuration
├── requirements/               # Python dependencies
├── docker-compose.yml          # Production Docker setup
└── Dockerfile                  # Production image
```

## Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=photo_checker --cov-report=html

# Run specific test file
pytest photo_checker/tests/test_api.py

# Run specific test
pytest photo_checker/tests/test_api.py::TestPhotoCheckAPI::test_analyze_white_background_image
```

## Deployment

### Production Checklist

- [ ] Set `DJANGO_SECRET_KEY` to a secure random value
- [ ] Set `DJANGO_DEBUG=False`
- [ ] Configure `DJANGO_ALLOWED_HOSTS`
- [ ] Set up PostgreSQL database
- [ ] Configure Redis for caching and Celery
- [ ] Set up SSL certificates
- [ ] Configure Sentry for error monitoring
- [ ] Review rate limiting settings
- [ ] Set up log aggregation
- [ ] Configure backup strategy

### Deploy with Docker

```bash
# Build and start services
docker-compose up -d --build

# Run migrations
docker-compose exec web python manage.py migrate

# Create superuser
docker-compose exec web python manage.py createsuperuser

# View logs
docker-compose logs -f web
```

## Performance

- Images are resized to max 1 megapixel for efficient processing
- Results are cached to avoid redundant processing
- Async processing available for batch operations
- Connection pooling for database and Redis
- Gzip compression enabled

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Run tests (`pytest`)
4. Run linting (`flake8 && black . && isort .`)
5. Commit changes (`git commit -m 'Add amazing feature'`)
6. Push to branch (`git push origin feature/amazing-feature`)
7. Open a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- OpenCV for image processing
- scikit-learn for K-Means clustering
- Django REST Framework for API development



