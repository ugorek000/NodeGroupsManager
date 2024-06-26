bl_info = {'name':"NodeGroupsManager", 'author':"ugorek",
           'version':(3,0,2), 'blender':(4,1,1), 'created':"2024.05.30",
           'warning':"", 'category':"Node",
           'tracker_url':"https://github.com/ugorek000/NodeGroupsManager/issues", 'wiki_url':""}
#№№ as package

from builtins import len as length
import bpy, re, functools

if __name__!="__main__":
    import sys
    assert __file__.endswith("__init__.py")
    sys.path.append(__file__[:-11])

import uu_ly

dict_classes = {}

class OpNone(bpy.types.Operator):
    bl_idname = 'ngm.none'
    bl_label = "OpNone"
    def execute(self, context):
        return {'FINISHED'}
dict_classes[OpNone] = True

class OpSimpleExec(bpy.types.Operator):
    bl_idname = 'ngm.simple_exec'
    bl_label = "OpSimpleExec"
    bl_options = {'UNDO'}
    exc: bpy.props.StringProperty(name="Exec", default="")
    def invoke(self, context, event):
        exec(self.exc)
        return {'FINISHED'}
dict_classes[OpSimpleExec] = True


def AddNdNgOp(context, nameNg):
    bpy.ops.node.add_node('INVOKE_DEFAULT', type=context.area.ui_type.replace("Tree","Group"), use_transform=True)
    context.space_data.edit_tree.nodes.active.node_tree = bpy.data.node_groups[nameNg]
def DelNgOp(context, nameNg, *, isFastDel=False):
    ng = bpy.data.node_groups[nameNg]
    if (isFastDel)or(uu_ly.ProcConfirmAlert(ng, limit=10.0)):
        bpy.data.node_groups.remove(ng)

dict_treeIcos = {"ShaderNodeTree":'NODE_MATERIAL', "GeometryNodeTree":'GEOMETRY_NODES', "CompositorNodeTree":'NODE_COMPOSITING', "TextureNodeTree":'NODE_TEXTURE'}

class PanelNodeGroupsManager(bpy.types.Panel):
    bl_idname = 'NGM_PT_NodeGroupsManager'
    bl_label = "NodeGroups Manager"
    bl_space_type = 'NODE_EDITOR'
    bl_region_type = 'TOOLS'
    isFirstDrawTgl = True
    @classmethod
    def poll(cls, context):
        return (tree:=context.space_data.edit_tree)and(tree.bl_idname in {"ShaderNodeTree", "GeometryNodeTree", "CompositorNodeTree", "TextureNodeTree"})
    def draw(self, context):
        colLy = self.layout.column()
        prefs = Prefs()
        isAllowDimHl1 = prefs.intAllowDimHl<1
        row = colLy.row(align=True)
        rowFilter = row.row(align=True)
        txt_filter = rowFilter.prop_and_get(prefs,'filter', text="", icon='SORTBYEXT')
        rowFilter.active = (isAllowDimHl1)or(not not txt_filter)
        rowFilter.separator()
        rowFilter.separator()
        rowIsParse = row.row(align=True)
        rowIsParse.alignment = 'CENTER'
        rowIsParse.active = isAllowDimHl1
        isParsePrefixes = rowIsParse.prop_and_get(prefs,'isParsePrefixes')
        ##
        list_data = [ng for ng in bpy.data.node_groups if ng.bl_idname==context.space_data.tree_type]
        if isParsePrefixes:
            dict_data = {ng.name:ng for ng in list_data}
            LIsDict = lambda ess: ess.__class__ is dict
            def RecrParsePrefixes(dict_recr):
                dict_parse = {}
                #Накопить по первому символу; из пустой строки словарь не делать
                for dk, dv in dict_recr.items():
                    if dk:
                        dict_parse.setdefault(dk[0], {})[dk[1:]] = dv
                    else:
                        dict_parse[""] = dv #"Прижали к стенке"; хорошо, что в обрабатываемых данных нет дубликатов.
                #Ядро рекурсии; продолжать скользить по веткам, если их больше одной
                for dk, dv in dict_parse.items():
                    if (dk)and(length(dv)>1):
                        dict_parse[dk] = RecrParsePrefixes(dv)
                dict_result = {} #Перенос -- вынужденный.
                #Убрать "одинокие" словари, и их содержимое пристыковать по ключу на уровень выше
                for dk, dv in dict_parse.items():
                    if (not LIsDict(dv))or(length(dv)!=1):
                        dict_result[dk] = dv
                    else:
                        di = tuple(dv.items())[0]
                        dict_result[dk+di[0]] = di[1]
                return dict_result
            limitTrigger = prefs.intGroupThresholdTrigger-1
            dict_hierarchy = RecrParsePrefixes(dict_data)
            def RecrParseHierarchy(txt_recr, dict_recr):
                def RecrCollapseGet(dict_recr):
                    list_result = []
                    for dk, dv in dict_recr.items():
                        if LIsDict(dv):
                            list_result.extend(RecrCollapseGet(dv))
                        else:
                            list_result.append(dv)
                    return list_result
                list_result = []
                sco = 0
                for dk, dv in dict_recr.items():
                    if not LIsDict(dv):
                        sco += 1
                    else:
                        break
                if sco>limitTrigger:
                    #Я не знаю, как наперёд узнать размер группы, чтобы иметь одинаковый результат с второй веткой limitTrigger;
                    # благодаря чему его можно будет переназвать на "intGroupThreshold".
                    list_result.append( (txt_recr, RecrCollapseGet(dict_recr)) )
                else:
                    for dk in dict_recr.keys():
                        break
                    if dk:
                        for dk, dv in dict_recr.items():
                            if LIsDict(dv):
                                list_result.extend(RecrParseHierarchy(txt_recr+dk, dv))
                            else:
                                list_result.append(dv)
                    else:
                        list_all = RecrCollapseGet(dict_recr)
                        if length(list_all)>limitTrigger:
                            list_result.append( (txt_recr, list_all) )
                        else:
                            list_result.extend(list_all)
                return list_result
            list_collapsed = RecrParseHierarchy("", dict_hierarchy)
        ##
        colList = colLy.column(align=True)
        isAllowAlertHl = prefs.isAllowAlertHl
        isAllowSelectHl = prefs.isAllowSelectHl
        isAllowDimHl2 = prefs.intAllowDimHl<2
        intStyleOrphans = prefs.intStyleOrphans
        patr = re.compile(txt_filter) if txt_filter else None
        list_ngPath = [pt.node_tree for pt in context.space_data.path]
        treeEdit = context.space_data.edit_tree
        soldTreeNdAc = getattr(ndAc,'node_tree', None) if (ndAc:=treeEdit.nodes.active)and(ndAc.select) else None
        set_selNdNg = set(nd.node_tree for nd in treeEdit.nodes if (nd.select)and(nd.type=='GROUP')and(nd.node_tree))
        def LyDrawItem(where, ng, *, styleOrphans=intStyleOrphans, styleSel=True, styleInPath=False):
            rowItem = where.row(align=True)
            if (not styleOrphans)and(ng.users.numerator==0):
                rowItem.label(text="", icon='DRIVER_TRANSFORM')
            rowDel = rowItem.row(align=True)
            tgl = not not uu_ly.ProcConfirmAlert(ng)
            rowDel.operator(OpSimpleExec.bl_idname, text="", icon='TRASH' if tgl else 'X').exc = f"DelNgOp(context, {repr(ng.name)}, isFastDel=event.shift)"
            rowDel.active = (isAllowDimHl1)or(tgl)
            rowName = rowItem.row(align=True)
            rowName.prop(ng,'name', text="", icon=dict_treeIcos[ng.bl_idname])
            ##
            row = rowItem.row(align=True)
            tgl = (ng.users.numerator==0)and(styleOrphans!=0)
            if styleOrphans==2:
                row.alert = (isAllowAlertHl)and(tgl)
            else:
                rowName.active = (isAllowDimHl2)or(not tgl)
            row.prop(ng,'use_fake_user', text="", icon='DRIVER_TRANSFORM' if tgl else 'NONE')
            row.active = (isAllowDimHl2)or(not tgl)
            ##
            rowAdd = rowItem.row(align=True)
            if isAllowAlertHl:
                if styleInPath:
                    rowAdd.alert = (ng in list_ngPath)or(ng==soldTreeNdAc)and(styleSel)
                else:
                    rowAdd.alert = (ng==treeEdit)or(ng==soldTreeNdAc)and(styleSel)
            fit = (ng in set_selNdNg) if styleSel else (ng==soldTreeNdAc)
            rowAdd.operator(OpSimpleExec.bl_idname, text="", icon='TRIA_RIGHT', depress=(isAllowSelectHl)and(fit)).exc = f"AddNdNgOp(context, {repr(ng.name)})"
            rowAdd.scale_x = 1.75
            rowAdd.active = (isAllowDimHl2)or(ng not in list_ngPath)or((styleInPath)and(ng==treeEdit))
        ##
        set_search = set(ng for ng in list_data if (not patr)or(re.search(patr, ng.name)))
        for li in list_collapsed if isParsePrefixes else list_data:
            if li.__class__ is tuple:
                list_ng = li[1]
                if (not patr)or(any(True for ng in list_ng if ng in set_search)):
                    colBox = colList.box().column(align=True)
                    if not( (ciUnf:=prefs.unfurils.get(li[0], None))and(ciUnf.nameRen==li[0]) ):
                        colBox.box().label()
                        bpy.app.timers.register(functools.partial(TimerAddUnfuril, prefs, li[0]))
                        continue
                    rowRootUnf = colBox.row(align=True)
                    rowTgl = rowRootUnf.row(align=True)
                    unf = rowTgl.prop_and_get(ciUnf,'unf', text="", icon='DOWNARROW_HLT' if ciUnf.unf else 'RIGHTARROW', emboss=False)
                    rowTgl.scale_x = 2.0
                    rowUnf = rowRootUnf.row(align=True)
                    rowCou = rowUnf.row().row(align=True)
                    rowCou.alignment = 'CENTER'
                    len = length(list_ng)
                    rowCou.ui_units_x = 0.5*(0.5+length(str(len)))
                    rowName = rowUnf.row(align=True)
                    if unf:
                        rowName.prop(ciUnf,'nameRen', text="") #todo0 слить макеты кнопки и поле имени вместе.
                    else:
                        rowName.separator()
                        rowName.label(text=ciUnf.name)
                    rowUnf.active = (isAllowDimHl2)or(not unf)
                    colUnfList = colBox.row().column(align=True)
                    if unf:
                        sco = 0
                        for ng in list_ng:
                            if ng in set_search:
                                LyDrawItem(colUnfList, ng)
                                sco += 1
                        tgl = False
                    else:
                        sco = len
                        tgl = False
                        if any(ng for ng in list_ng if ng==treeEdit):
                            rowCou.alert = isAllowAlertHl
                            rowCou.active = isAllowDimHl2
                        elif any(ng for ng in list_ng if ng==soldTreeNdAc):
                            rowCou.alert = isAllowAlertHl
                            tgl = True
                        elif any(ng for ng in list_ng if ng in set_selNdNg):
                            tgl = True
                    rowCou.operator(OpNone.bl_idname, text=str(sco), depress=(isAllowSelectHl)and(tgl))
            else:
                if li in set_search:
                    LyDrawItem(colList, li)
        if self.isFirstDrawTgl:
            self.__class__.isFirstDrawTgl = False
            bpy.app.timers.register(functools.partial(TimerAllUnfToFalse, prefs))
        ##
        if (_debug:=False)and(isParsePrefixes):
            def RecrView(where, dict_recr):
                col = where.column(align=True)
                for dk, dv in dict_recr.items():
                    if LIsDict(dv):
                        col.label(text=dk)
                        row = col.row(align=True)
                        row.label(icon='BLANK1')
                        RecrView(row, dv)
                    else:
                        rowItem = col.row(align=True)
                        row = rowItem.row(align=True)
                        row.alignment = 'CENTER'
                        if dk:
                            row.label(text=dk+": ")
                        else:
                            row = rowItem.row(align=True)
                            row.alignment = 'CENTER'
                            row.label(text="\"\": ")
                            row.active = False
                        rowItem.alert = True
                        rowItem.label(text=str(dv.name))
            if False:
                for li in list_collapsed:
                    row = colLy.row(align=True)
                    row.alert = True
                    row.label(text=str(li))
            colLy.label(text=str(dict_hierarchy))
            RecrView(colLy, dict_hierarchy)

def TimerAllUnfToFalse(prefs):
    for ci in prefs.unfurils:
        ci.unf = False
def TimerAddUnfuril(prefs, name):
    ci = prefs.unfurils.get(name) or prefs.unfurils.add()
    ci.name = name
    ci.nameRen = name
def UpdateNameRen(self, context):
    if self.name!=self.nameRen:
        for ng in tuple(bpy.data.node_groups):
            if ng.name.startswith(self.name):
                ng.name = ng.name.replace(self.name, self.nameRen, 1)
class Unfuril(bpy.types.PropertyGroup):
    unf: bpy.props.BoolProperty(default=True)
    nameRen: bpy.props.StringProperty(default="", update=UpdateNameRen)
dict_classes[Unfuril] = True

def Prefs():
    return bpy.context.preferences.addons[bl_info['name']].preferences

class AddonPrefs(bpy.types.AddonPreferences):
    bl_idname = bl_info['name'] if __name__=="__main__" else __name__
    filter: bpy.props.StringProperty(name="Filter", default="(?i).*")
    isParsePrefixes: bpy.props.BoolProperty(name="Parse prefixes", default=True)
    intGroupThresholdTrigger: bpy.props.IntProperty(name="Threshold trigger", min=0, soft_min=3, soft_max=10, default=3)
    unfurils: bpy.props.CollectionProperty(type=Unfuril)
    isCloseByDefault: bpy.props.BoolProperty(name="Default Closed", default=False)
    intOrderPanel: bpy.props.IntProperty(name="Panel Order", default=2)
    isAllowAlertHl: bpy.props.BoolProperty(name="Alert Highlighting", default=True)
    isAllowSelectHl: bpy.props.BoolProperty(name="Select Highlighting", default=True)
    intAllowDimHl: bpy.props.IntProperty(name="Dim Highlighting", min=0, max=2, default=2)
    intStyleOrphans: bpy.props.IntProperty(name="Style Orphans", min=0, max=2, default=1)
    def draw(self, context):
        def LyLeftProp(where, who, prop):
            row = where.row()
            #row.alignment = 'LEFT'
            row.prop(who, prop)
        colMain = self.layout.column()
        box = uu_ly.LyAddHeaderedBox(colMain, "options", active=False)
        colProps = box.column()
        colProps.prop(self,'isParsePrefixes')
        row = colProps.row()
        LyLeftProp(row, self,'intGroupThresholdTrigger')
        row.active = (self.isParsePrefixes)and(self.intGroupThresholdTrigger>2)
        colProps.separator()
        colProps.prop(self,'isCloseByDefault', text="Panel Closed by Default") #"Panel Default Closed"
        LyLeftProp(colProps, self,'intOrderPanel')
        colProps.separator()
        colProps.prop(self,'isAllowAlertHl')
        colProps.prop(self,'isAllowSelectHl')
        LyLeftProp(colProps, self,'intAllowDimHl')
        LyLeftProp(colProps, self,'intStyleOrphans')
dict_classes[AddonPrefs] = True

def register():
    for dk in dict_classes:
        bpy.utils.register_class(dk)
    prefs = Prefs()
    PanelNodeGroupsManager.bl_order = prefs.intOrderPanel
    if prefs.isCloseByDefault:
        PanelNodeGroupsManager.bl_options = {'DEFAULT_CLOSED'}
    bpy.utils.register_class(PanelNodeGroupsManager)
    ##
    prefs.filter = ""
    prefs.unfurils.clear()
def unregister():
    bpy.utils.unregister_class(PanelNodeGroupsManager)
    for dk in reversed(dict_classes):
        bpy.utils.unregister_class(dk)

if __name__=="__main__":
    register()
