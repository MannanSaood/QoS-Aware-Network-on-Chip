#include <tcl.h>
#include "../../algorithms/common/select.hpp"
static int Select(ClientData,Tcl_Interp* ip,int argc,Tcl_Obj* const argv[]) {
    if(argc!=8) {Tcl_WrongNumArgs(ip,1,argv,"algorithm k source current dest occupancy peak");return TCL_ERROR;}
    int k,s,c,d;
    if(Tcl_GetIntFromObj(ip,argv[2],&k)!=TCL_OK || Tcl_GetIntFromObj(ip,argv[3],&s)!=TCL_OK ||
       Tcl_GetIntFromObj(ip,argv[4],&c)!=TCL_OK || Tcl_GetIntFromObj(ip,argv[5],&d)!=TCL_OK) return TCL_ERROR;
    if(k<2 || s<0 || c<0 || d<0 || s>=k*k || c>=k*k || d>=k*k) {
        Tcl_SetObjResult(ip,Tcl_NewStringObj("invalid mesh coordinate",-1));return TCL_ERROR;
    }
    noc::Load q,peak;
    for(int j=0;j<2;++j) {
        int n; Tcl_Obj** values;
        if(Tcl_ListObjGetElements(ip,argv[6+j],&n,&values)!=TCL_OK) return TCL_ERROR;
        if(n!=4) {Tcl_SetObjResult(ip,Tcl_NewStringObj("load needs four ports",-1));return TCL_ERROR;}
        for(int p=0;p<4;++p) {
            double x;
            if(Tcl_GetDoubleFromObj(ip,values[p],&x)!=TCL_OK) return TCL_ERROR;
            (j==0?q:peak)[p]=x;
        }
    }
    try {Tcl_SetObjResult(ip,Tcl_NewIntObj(noc::select(Tcl_GetString(argv[1]),s,c,d,k,q,peak)));}
    catch(const std::exception& e){Tcl_SetObjResult(ip,Tcl_NewStringObj(e.what(),-1));return TCL_ERROR;}
    return TCL_OK;
}
extern "C" int Nocroute_Init(Tcl_Interp* ip) {
    Tcl_CreateObjCommand(ip,"noc_select",Select,nullptr,nullptr);
    return Tcl_PkgProvide(ip,"nocroute","1.0");
}
