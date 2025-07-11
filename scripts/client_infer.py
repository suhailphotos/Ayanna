# inside hda inference script
# pythonSOP Path: '/obj/rndForest/rndforest/inference'


import hou
import requests
import pandas as pd


# Get the geometry from input 0 (training points with Cd, class, rndf_class)
geo_train = hou.pwd().inputs()[0].geometry()
# Get the geometry from input 1 (new query points)
geo_query = hou.pwd().inputs()[1].geometry()
geo = hou.pwd().geometry()

# 1. Gather query positions from input 1
query_points = []
for pt in geo_query.points():
    pos = pt.position()
    query_points.append([pos[0], pos[1], pos[2]])
    
# 2. Predict class labels via API
url = f"{hou.getenv('RNDFOREST_API_URL')}/predict"
response = requests.post(url, json={"points": query_points})
pred_classes = response.json()["predictions"]

# 3. Build a lookup table from rndf_class -> (Cd, class) using input 0
#   (Assume there is at least one point for each rndf_class)
class_lookup = {}
for pt in geo_train.points():
    rndf_class = pt.intAttribValue("rndf_class")
    color = pt.attribValue("Cd")  # tuple of 3 floats
    conn_class = pt.intAttribValue("class")  # Houdini connectivity SOP's class
    class_lookup[rndf_class] = {"Cd": color, "class": conn_class}
    
# 4. Output geometry: For each query point, set predicted class, Cd, and class attribute
geo.clear()
rndf_class_attrib = geo.addAttrib(hou.attribType.Point, "rndf_class", 0)
cd_attrib = geo.addAttrib(hou.attribType.Point, "Cd", (1.0, 1.0, 1.0))
class_attrib = geo.addAttrib(hou.attribType.Point, "class", 0)


for i, pt in enumerate(query_points):
    newpt = geo.createPoint()
    newpt.setPosition(pt)
    predicted_class = pred_classes[i]
    # Copy color/class from training data
    info = class_lookup.get(predicted_class, None)
    if info:
        newpt.setAttribValue(rndf_class_attrib, predicted_class)
        newpt.setAttribValue(cd_attrib, info["Cd"])
        newpt.setAttribValue(class_attrib, info["class"])
    else:
        # fallback: assign default color/class if not found
        newpt.setAttribValue(rndf_class_attrib, predicted_class)
        newpt.setAttribValue(cd_attrib, (1.0, 0.0, 0.0))
        newpt.setAttribValue(class_attrib, -1)

