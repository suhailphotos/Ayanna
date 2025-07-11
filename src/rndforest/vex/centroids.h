vector centroid = {0.0, 0.0, 0.0};
int npts = npoints(0);

for (int i = 0; i < npts; i++) {
    centroid += point(0, "P", i);
}
if (npts > 0)
    centroid /= npts;
    
// Create a new point at the centroid
int newpt = addpoint(0, centroid);


int classval = prim(0, "class", 0);
int rndf_classval = prim(0, "rndf_class", 0);
vector col = prim(0, "Cd", 0); 
setpointattrib(0, "class", newpt, classval, "set");
setpointattrib(0, "rndf_class", newpt, rndf_classval, "set");
setpointattrib(0, "Cd", newpt, col, "set");

for (int i = 0; i < npts; i++)
    removepoint(0, i);

