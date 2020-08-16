try:
    import unzip_requirements
except ImportError:
    pass
    
from PIL import Image

import boto3
import os
import io
import json
import base64
import cv2
import dlib
from requests_toolbelt.multipart import decoder
print("Import End...")

S3_BUCKET = os.environ['S3_BUCKET'] if 'S3_BUCKET' in os.environ else 'evadebs1'
MODEL_PATH = os.environ['MODEL_PATH'] if 'MODEL_PATH' else 'shape_predictor_68_face_landmarks.dat'

print('Downloading model...')
s3 = boto3.client('s3')
print('Downloaded model...')

try:
    if os.path.isfile(MODEL_PATH) != True:
        print('ModelPath exists...')
        obj = s3.get_object(Bucket=S3_BUCKET, Key=MODEL_PATH)
        print('Creating ByteStream')
        bytestream = io.BytesIO(obj['Body'].read())
        with open(MODEL_PATH, "wb") as outfile:
            # Copy the BytesIO stream to the output file
            outfile.write(bytestream.getbuffer())
        print("Loading Model")
        detector = dlib.get_frontal_face_detector()
        predictor = dlib.shape_predictor("shape_predictor_68_face_landmarks.dat")
        print("Model Loaded...")
except Exception as e:
    print(repr(e))
    raise(e)
print('model. is ready..')

def get_prediction(image_bytes):
    tensor = transform_image(image_bytes=image_bytes)
    return model(tensor).argmax().item()
    
def face_swap_image(event, context):
    try:
        print('classify_image')
        
        body = base64.b64decode(event["body"])
        picture1 = decoder.MultipartDecoder(body, content_type_header).parts[0]
        im_arr1 = np.frombuffer(picture1.content, dtype=np.uint8)
        img1 = cv2.imdecode(im_arr1, flags=cv2.IMREAD_COLOR)
        picture2 = decoder.MultipartDecoder(body, content_type_header).parts[1]
        im_arr2 = np.frombuffer(picture2.content, dtype=np.uint8)
        img2 = cv2.imdecode(im_arr2, flags=cv2.IMREAD_COLOR)
        body = base64.b64decode(event['body'])
        print('BODY LOADED')
        
        points1 = fbc.getLandmarks(detector, predictor, img1)
        points2 = fbc.getLandmarks(detector, predictor, img2)
        
        # Find convex hull
        hullIndex = cv2.convexHull(np.array(points2), returnPoints=False)

        # Create convex hull lists
        hull1 = []
        hull2 = []
        for i in range(0, len(hullIndex)):
            hull1.append(points1[hullIndex[i][0]])
            hull2.append(points2[hullIndex[i][0]])

        #Find Delaunay traingulation for convex hull points
        sizeImg2 = img2.shape    
        rect = (0, 0, sizeImg2[1], sizeImg2[0])

        dt = fbc.calculateDelaunayTriangles(rect, hull2)

        # If no Delaunay Triangles were found, quit
        if len(dt) == 0:
            quit()

        imTemp1 = im1Display.copy()
        imTemp2 = im2Display.copy()

        tris1 = []
        tris2 = []
        for i in range(0, len(dt)):
            tri1 = []
            tri2 = []
            for j in range(0, 3):
                tri1.append(hull1[dt[i][j]])
                tri2.append(hull2[dt[i][j]])

            tris1.append(tri1)
            tris2.append(tri2)

        cv2.polylines(imTemp1,np.array(tris1),True,(0,0,255),2); 
        cv2.polylines(imTemp2,np.array(tris2),True,(0,0,255),2);
        
        output = cv2.seamlessClone(np.uint8(img1Warped), img2, mask, center, cv2.NORMAL_CLONE)
        # Simple Alpha Blending
        # Apply affine transformation to Delaunay triangles
        for i in range(0, len(tris1)):
            fbc.warpTriangle(img1, img1Warped, tris1[i], tris2[i])
        
        
            filename = picture.headers[b'Content-Disposition'].decode().split(';')[2].split('=')[1]
            
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Credentials': True
            },
            'body': json.dumps({'file': filename.replace('"', ''), 'predicted': prediction})
        }
    except Exception as e:
        print(repr(e))
        return {
            "statusCode": 500,
            "headers": {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Credentials': True
            },
            'body': json.dumps({'error': repr(e)})
        }
