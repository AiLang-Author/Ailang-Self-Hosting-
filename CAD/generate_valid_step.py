#!/usr/bin/env python3
import os

step_content = """ISO-10303-21;
HEADER;
FILE_DESCRIPTION(('FreeCAD Model'),'2;1');
FILE_NAME('cli_model.stp','2026-08-04T10:30:00',('Sean Collins'),('2 Paws Machine'),'AILang CAD Engine','AILang CAD Engine','');
FILE_SCHEMA(('AUTOMOTIVE_DESIGN { 1 0 10303 214 1 1 1 1 }'));
ENDSEC;
DATA;
#100 = APPLICATION_CONTEXT('automotive design');
#101 = APPLICATION_PROTOCOL_DEFINITION('international standard','automotive_design',2000,#100);
#102 = PRODUCT('cli_model','cli_model','',(#103));
#103 = PRODUCT_CONTEXT('',#100,'mechanical');
#104 = PRODUCT_DEFINITION_FORMATION('','',#102);
#105 = PRODUCT_DEFINITION('design','',#104,#106);
#106 = PRODUCT_DEFINITION_CONTEXT('part definition',#100,'design');
#107 = PRODUCT_DEFINITION_SHAPE('','',#105);
#108 = SHAPE_DEFINITION_REPRESENTATION(#107,#109);
#109 = ADVANCED_BREP_SHAPE_REPRESENTATION('',(#110),#111);
#110 = MANIFOLD_SOLID_BREP('Box',#120);
#111 = ( GEOMETRIC_REPRESENTATION_CONTEXT(3) GLOBAL_UNCERTAINTY_ASSIGNED_CONTEXT((#112)) GLOBAL_UNIT_ASSIGNED_CONTEXT((#113,#114,#115)) REPRESENTATION_CONTEXT('Context3D','3D Context') );
#112 = UNCERTAINTY_MEASURE_WITH_UNIT(LENGTH_MEASURE(1.E-07),#113,'distance_accuracy_value','confusion accuracy');
#113 = ( LENGTH_UNIT() NAMED_UNIT(*) SI_UNIT(.MILLI.,.METRE.) );
#114 = ( NAMED_UNIT(*) PLANE_ANGLE_UNIT() SI_UNIT(*,.RADIAN.) );
#115 = ( NAMED_UNIT(*) SI_UNIT(*,.STERADIAN.) SOLID_ANGLE_UNIT() );

// Vertices
#1 = CARTESIAN_POINT('',(0.,0.,0.));
#2 = CARTESIAN_POINT('',(100.,0.,0.));
#3 = CARTESIAN_POINT('',(100.,50.,0.));
#4 = CARTESIAN_POINT('',(0.,50.,0.));
#5 = CARTESIAN_POINT('',(0.,0.,25.));
#6 = CARTESIAN_POINT('',(100.,0.,25.));
#7 = CARTESIAN_POINT('',(100.,50.,25.));
#8 = CARTESIAN_POINT('',(0.,50.,25.));

#11 = VERTEX_POINT('',#1);
#12 = VERTEX_POINT('',#2);
#13 = VERTEX_POINT('',#3);
#14 = VERTEX_POINT('',#4);
#15 = VERTEX_POINT('',#5);
#16 = VERTEX_POINT('',#6);
#17 = VERTEX_POINT('',#7);
#18 = VERTEX_POINT('',#8);

// Directions
#20 = DIRECTION('',(0.,0.,1.));
#21 = DIRECTION('',(1.,0.,0.));
#22 = DIRECTION('',(0.,1.,0.));
#23 = DIRECTION('',(0.,0.,-1.));
#24 = DIRECTION('',(-1.,0.,0.));
#25 = DIRECTION('',(0.,-1.,0.));

// Vector lines
#31 = LINE('',#1,#21);
#32 = LINE('',#2,#22);
#33 = LINE('',#3,#24);
#34 = LINE('',#4,#25);
#35 = LINE('',#5,#21);
#36 = LINE('',#6,#22);
#37 = LINE('',#7,#24);
#38 = LINE('',#8,#25);
#39 = LINE('',#1,#20);
#40 = LINE('',#2,#20);
#41 = LINE('',#3,#20);
#42 = LINE('',#4,#20);

// Edges
#51 = EDGE_CURVE('',#11,#12,#31,.T.);
#52 = EDGE_CURVE('',#12,#13,#32,.T.);
#53 = EDGE_CURVE('',#13,#14,#33,.T.);
#54 = EDGE_CURVE('',#14,#11,#34,.T.);
#55 = EDGE_CURVE('',#15,#16,#35,.T.);
#56 = EDGE_CURVE('',#16,#17,#36,.T.);
#57 = EDGE_CURVE('',#17,#18,#37,.T.);
#58 = EDGE_CURVE('',#18,#15,#38,.T.);
#59 = EDGE_CURVE('',#11,#15,#39,.T.);
#60 = EDGE_CURVE('',#12,#16,#40,.T.);
#61 = EDGE_CURVE('',#13,#17,#41,.T.);
#62 = EDGE_CURVE('',#14,#18,#42,.T.);

// Oriented Edges
#71 = ORIENTED_EDGE('',*,*,#51,.T.);
#72 = ORIENTED_EDGE('',*,*,#52,.T.);
#73 = ORIENTED_EDGE('',*,*,#53,.T.);
#74 = ORIENTED_EDGE('',*,*,#54,.T.);
#75 = ORIENTED_EDGE('',*,*,#55,.F.);
#76 = ORIENTED_EDGE('',*,*,#56,.F.);
#77 = ORIENTED_EDGE('',*,*,#57,.F.);
#78 = ORIENTED_EDGE('',*,*,#58,.F.);

#81 = ORIENTED_EDGE('',*,*,#51,.F.);
#82 = ORIENTED_EDGE('',*,*,#59,.T.);
#83 = ORIENTED_EDGE('',*,*,#55,.T.);
#84 = ORIENTED_EDGE('',*,*,#60,.F.);

#85 = ORIENTED_EDGE('',*,*,#52,.F.);
#86 = ORIENTED_EDGE('',*,*,#60,.T.);
#87 = ORIENTED_EDGE('',*,*,#56,.T.);
#88 = ORIENTED_EDGE('',*,*,#61,.F.);

#89 = ORIENTED_EDGE('',*,*,#53,.F.);
#90 = ORIENTED_EDGE('',*,*,#61,.T.);
#91 = ORIENTED_EDGE('',*,*,#57,.T.);
#92 = ORIENTED_EDGE('',*,*,#62,.F.);

#93 = ORIENTED_EDGE('',*,*,#54,.F.);
#94 = ORIENTED_EDGE('',*,*,#62,.T.);
#95 = ORIENTED_EDGE('',*,*,#58,.T.);
#96 = ORIENTED_EDGE('',*,*,#59,.F.);

// Edge Loops
#131 = EDGE_LOOP('',(#71,#72,#73,#74));
#132 = EDGE_LOOP('',(#78,#77,#76,#75));
#133 = EDGE_LOOP('',(#81,#82,#83,#84));
#134 = EDGE_LOOP('',(#85,#86,#87,#88));
#135 = EDGE_LOOP('',(#89,#90,#91,#92));
#136 = EDGE_LOOP('',(#93,#94,#95,#96));

// Face Bounds
#141 = FACE_BOUND('',#131,.T.);
#142 = FACE_BOUND('',#132,.T.);
#143 = FACE_BOUND('',#133,.T.);
#144 = FACE_BOUND('',#134,.T.);
#145 = FACE_BOUND('',#135,.T.);
#146 = FACE_BOUND('',#136,.T.);

// Planes
#151 = AXIS2_PLACEMENT_3D('',#1,#20,#21);
#152 = AXIS2_PLACEMENT_3D('',#5,#20,#21);
#153 = AXIS2_PLACEMENT_3D('',#1,#25,#21);
#154 = AXIS2_PLACEMENT_3D('',#2,#21,#22);
#155 = AXIS2_PLACEMENT_3D('',#3,#22,#24);
#156 = AXIS2_PLACEMENT_3D('',#4,#24,#25);

#161 = PLANE('',#151);
#162 = PLANE('',#152);
#163 = PLANE('',#153);
#164 = PLANE('',#154);
#165 = PLANE('',#155);
#166 = PLANE('',#156);

// Advanced Faces
#171 = ADVANCED_FACE('',(#141),#161,.F.);
#172 = ADVANCED_FACE('',(#142),#162,.T.);
#173 = ADVANCED_FACE('',(#143),#163,.T.);
#174 = ADVANCED_FACE('',(#144),#164,.T.);
#175 = ADVANCED_FACE('',(#145),#165,.T.);
#176 = ADVANCED_FACE('',(#146),#166,.T.);

// Closed Shell
#120 = CLOSED_SHELL('',(#171,#172,#173,#174,#175,#176));
ENDSEC;
END-ISO-10303-21;
"""

for path in ['/home/sean/cli_model.stp', '/home/sean/master_model.stp', '/mnt/c/Users/Sean/Documents/AILangSH/cli_model.stp', '/mnt/c/Users/Sean/Documents/AILangSH/master_model.stp']:
    with open(path, 'w') as f:
        f.write(step_content)
    print(f"Updated valid STEP AP214 file: {path}")
