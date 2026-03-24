import base64
import logging
from typing import List, Optional

from fastapi import FastAPI, File, Form, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response

from . import emotion_gender_processor as eg_processor

app = FastAPI(title='face-classification-api')

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        'http://localhost:5173',
        'http://127.0.0.1:5173',
        'http://localhost:3000',
        'http://127.0.0.1:3000',
    ],
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)


def _parse_belief_confidence(raw_value):
    if raw_value is None or raw_value == '':
        return None
    value = float(raw_value)
    if value > 1.0:
        value = value / 100.0
    if value < 0.0 or value > 1.0:
        raise ValueError('belief_confidence must be in [0,1] or [0,100].')
    return round(value, 2)


@app.get('/')
def index():
    return {
        'service': 'face-classification-api',
        'status': 'ok',
        'framework': 'fastapi',
        'endpoints': ['/api/health', '/api/classify', '/api/classify/frames', '/classifyImage', '/docs']
    }


@app.get('/api/health')
def health():
    return {'status': 'ok'}


@app.post('/api/classify')
async def classify(
    image: UploadFile = File(...),
    belief_confidence: Optional[str] = Form(None),
    include_image: bool = Query(False),
    detailed: bool = Query(False),
):
    try:
        image_bytes = await image.read()
        parsed_belief_confidence = _parse_belief_confidence(belief_confidence)

        result = eg_processor.classify_image(image_bytes)
        if detailed:
            response = {
                'faces_detected': result['faces_detected'],
                'predictions': result['predictions']
            }
        else:
            response = eg_processor.get_primary_prediction(
                result['predictions'], belief_confidence=parsed_belief_confidence)

        if include_image:
            response['annotated_image_base64'] = base64.b64encode(
                result['annotated_image_bytes']).decode('utf-8')

        return response
    except ValueError as err:
        raise HTTPException(status_code=400, detail=str(err))
    except Exception as err:
        logging.error('An error has occurred whilst processing the file: "{0}"'.format(err))
        raise HTTPException(status_code=400, detail='We cannot process the file sent in the request.')


@app.post('/api/classify/frames')
async def classify_frames(
    images: Optional[List[UploadFile]] = File(None),
    image: Optional[List[UploadFile]] = File(None),
    belief_confidence: Optional[str] = Form(None),
):
    try:
        files = images or image or []
        if not files:
            raise HTTPException(status_code=400,
                                detail='Missing image files. Use form-data key "images" (or repeated "image").')

        parsed_belief_confidence = _parse_belief_confidence(belief_confidence)
        image_payloads = []
        for uploaded_file in files:
            payload = await uploaded_file.read()
            if payload:
                image_payloads.append(payload)

        if not image_payloads:
            raise HTTPException(status_code=400, detail='No valid image payloads provided.')

        return eg_processor.classify_images(image_payloads,
                                            belief_confidence=parsed_belief_confidence)
    except ValueError as err:
        raise HTTPException(status_code=400, detail=str(err))
    except HTTPException:
        raise
    except Exception as err:
        logging.error('An error has occurred whilst processing frame files: "{0}"'.format(err))
        raise HTTPException(status_code=400, detail='We cannot process the file sent in the request.')


@app.post('/classifyImage')
async def upload(image: UploadFile = File(...)):
    try:
        image_bytes = await image.read()
        result = eg_processor.classify_image(image_bytes)
        return Response(
            content=result['annotated_image_bytes'],
            media_type='image/png',
            headers={'Content-Disposition': 'attachment; filename=predicted_image.png'}
        )
    except Exception as err:
        logging.error('An error has occurred whilst processing the file: "{0}"'.format(err))
        raise HTTPException(status_code=400, detail='We cannot process the file sent in the request.')


@app.exception_handler(404)
async def not_found(_, __):
    return JSONResponse(status_code=404, content={'error': 'Resource no found.'})


if __name__ == '__main__':
    import uvicorn

    uvicorn.run('web.faces:app', host='0.0.0.0', port=8084, reload=False)
