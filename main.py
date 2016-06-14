###Imports###
# PIL and tkinter has conflicting names, so we do this.
import PIL.Image
import PIL.ImageTk
import PIL.ImageOps

from tkinter import *
from tkinter.ttk import *
from tkinter import filedialog

from io import BytesIO
import os
import webbrowser
import traceback

###Constants###
s='''
!Scripting
You can enter a python script here to be run, to fully customize your conversion process.

The script can use all the builtin functions of Python3.
You can print to the standard output using print(). Those will show up in the console window.

!Input
The python script is given these variables:

Filename : The filename.
Extension : The filename extension.
Filename_no_extension : Filename with its extension stripped.
Width : The width of the source image.
Height : The height of the source image.
Mode : Image mode of the source image.
Size : The size of the source image file, in bytes.
These variables are in the global namespace; you can use them like any other python variable.

!Return values
The python script should end with a return statement. The return statement should return a single dict, with all the image conversion parameters.

The dict MUST have these elements:
"Filename" : The filename of the converted image.
"Type" : The file type. Supported types are "JPEG", "GIF", "PNG", "BMP", or "JPEG2000","Copy", and "Pass". "Copy" will copy the image file without re-encoding, and "Pass" will simply skip the image.

Some file types require additional dict elements.

JPEG:
    "Quality" : Integer value from 1 to 100.
    "Subsampling" : Integer value from 0 to 2. 0=4:4:4, 1=4:2:2, 2=4:1:1

PNG:
    "Compression" : Integer value from 0 to 9.


You can resize images by including the "Resize" element.
The "Resize" element should be a tuple, containg two elements, for the desired X and Y size.
You can also specify the sampling method, by including the "Resize_sampling" element. Valid values are "Nearest Neighbor", "Bilinear","Bicubic" and "Lanczos". If not supplied, it defaults to Bicubic sampling.


!Example code
print("hello world")
if Extension.lower()==".gif": #We can't convert animated GIFs, copy them as is.
    return {"Type":"Copy","Filename":Filename}
if Width>1000: #If the width is too long, trim it down to 1000 pixels.
    return {"Type":"JPEG","Filename":"Converted_"+Filename_no_extension+".jpeg","Quality":70,"Subsampling":0,
            "Resize":(1000,int(1000/Width*Height)),"Resize_sampling":"Bicubic"}
if Height>1000: #If the height is too long, trim it down to 1000 pixels.
    return {"Type":"JPEG","Filename":"Converted_"+Filename_no_extension+".jpeg","Quality":70,"Subsampling":0,
            "Resize":(int(1000/Height*Width),1000),"Resize_sampling":"Bicubic"}
return {"Filename":Filename,"Type":"PNG","Compression":7} #Others just convert to PNG.
'''

###Classes###
class Bindable:
    '''Base class for classes implementing an Observer pattern.'''
    def __init__(self, **kwargs):
        # pass
        self._callbacks = list()
        super().__init__(**kwargs)

    def bind(self, callbcak):
        self._callbacks.append(callbcak)

    def _callback(self):
        for i in self._callbacks:
            i()

    def unbind(self,obj):
        self._callbacks.remove(obj)



class SliderPlus(Bindable, Frame):
    '''Slider with a label and a value display.
REQUIRES these keyword argumemts:
plus_name, plus_max,plus_min,plus_divisions,plus_format
'''
    def __init__(self, **kw):
        # Variables
        self._plus_name = kw["plus_name"]
        self._plus_max = kw["plus_max"]
        self._plus_min = kw["plus_min"]
        self._plus_divisions = kw["plus_divisions"]
        self._plus_format = kw["plus_format"]
        self._plus_value = self._plus_min


        # This is ugly.(duh)
        del kw["plus_name"]
        del kw["plus_max"]
        del kw["plus_min"]
        del kw["plus_divisions"]
        del kw["plus_format"]

        try:
            self._plus_display_override=kw['plus_display_override']
            del kw['plus_display_override']
        except KeyError:
            self._plus_display_override=None
            pass

        super().__init__(**kw)


        # Label
        self._plus_label = Label(self, text=self._plus_name)
        self._plus_label.grid(row=1, column=1)

        # Slider
        self._plus_slider = Scale(self, orient=HORIZONTAL, length=200, from_=0, to=self._plus_divisions, value=0,
                                  command=self._plus_slider_changed)
        self._plus_slider.grid(column=2, row=1, padx=5,sticky=(W, E))
        self.columnconfigure(2, weight=1)
        self._plus_slider.bind("<ButtonRelease>", self._slider_released)
        self.columnconfigure(2,weight=1)
        # Value
        self._plus_value_str_label = Label(self, text=str(self._plus_min))
        self._plus_value_str_label.grid(column=3, row=1, sticky=(W, E))


        self._plus_slider_changed(self._plus_min)

    def _slider_released(self, evt):
        self._callback()

    def _plus_slider_changed(self, x):
        self._plus_value = int(round(float(x))) / self._plus_divisions * (
                            self._plus_max - self._plus_min) + self._plus_min
        #print(type(self._plus_value))
        if self._plus_display_override==None:
            self._plus_value_str_label.configure(text=("{:." + str(self._plus_format) + "f}").format(self._plus_value))
        else:
            self._plus_value_str_label.configure(text=self._plus_display_override(self._plus_value))

    def get_value(self):
        return self._plus_value



class ImageParameterPane(Frame):
    '''This class generates an image parameter pane, containing all the parameters for the image compression.
After parameters are changed, it compresses the source_image and replaces image
If source_image is not supplied, it will default to a image-less mode, where it is not bound to any other image.
'''
    def __init__(self, image=None, source_image=None, **kw):

        super().__init__(**kw)
        #Variables
        self._image = image
        self._source_image = source_image

        self._params = None
        self._image_data = None

        # UI
        self._notebook = Notebook(self)
        self._notebook.grid(column=1, row=1, sticky=(W, E, N, S))
        self._notebook.bind("<ButtonRelease>", lambda e: self._rerender_image())
        self.columnconfigure(1, weight=1)

        # UI>PNG
        self._tab_png = Frame(self)
        self._png_slider_compression = SliderPlus(plus_name="Compression", plus_divisions=9, plus_format=0,
                                                  plus_min=0, plus_max=9,  master=self._tab_png)
        self._png_slider_compression.grid(column=1, row=1, sticky=(W, E, N, S))
        self._png_slider_compression.bind(self._rerender_image)
        self._tab_png.columnconfigure(1,weight=1)
        #UI>JPEG
        self._tab_jpeg = Frame(self)
        self._jpeg_slider_quality = SliderPlus(plus_name="Quality", plus_divisions=99, plus_format=0,
                                               plus_min=1, plus_max=100, master=self._tab_jpeg)
        self._jpeg_slider_quality.grid(column=1, row=1, sticky=(W, E, N, S))
        self._jpeg_slider_quality.bind(self._rerender_image)

        self._jpeg_slider_subsampling = SliderPlus(plus_name="Chroma Subsampling", plus_divisions=2, plus_format=0,
                                                   plus_min=0, plus_max=2,
                                                   plus_display_override= lambda x:["4:4:4","4:2:2","4:1:1"][int(round(x))],
                                                   master=self._tab_jpeg)
        self._jpeg_slider_subsampling.grid(column=1, row=2, sticky=(W, E, N, S))
        self._jpeg_slider_subsampling.bind(self._rerender_image)
        self._tab_jpeg.columnconfigure(1,weight=1)
        #UI>GIF
        self._tab_gif = Frame(self)
        self._gif_label = Label(self._tab_gif, text="No Options.")
        self._gif_label.grid(column=1, row=1, sticky=(W, E, N, S))
        self._tab_gif.columnconfigure(1, weight=1)
        self._tab_gif.columnconfigure(1,weight=1)
        #UI>BMP
        self._tab_bmp = Frame(self)
        self._bmp_label = Label(self._tab_bmp, text="No Options.")
        self._bmp_label.grid(column=1, row=1, sticky=(W, E, N, S))
        self._tab_bmp.columnconfigure(1, weight=1)
        self._tab_bmp.columnconfigure(1,weight=1)
        #UI>JPEG2000
        self._tab_jpeg2 = Frame(self)
        self._jpeg2_label = Label(self._tab_jpeg2, text="Well...(Click here)", foreground="blue", cursor="hand2")
        self._jpeg2_label.bind("<Button-1>",
                               lambda e: webbrowser.open_new(r"https://github.com/python-pillow/Pillow/issues/1945"))
        self._jpeg2_label.grid(column=1, row=1, sticky=(W, E, N, S))

        self._notebook.add(self._tab_png, text="PNG")
        self._notebook.add(self._tab_gif, text="GIF")
        self._notebook.add(self._tab_jpeg, text="JPEG")
        self._notebook.add(self._tab_bmp, text="BMP")
        self._notebook.add(self._tab_jpeg2, text="JPEG2000")
        self._tab_jpeg2.columnconfigure(1,weight=1)


        if source_image==None:
            return

        #UI>Bottom buttons and labels
        self._actions = Frame(self)
        self._actions.grid(column=1, row=2, sticky=(W, E, N, S))

        self._actions_save = Button(self._actions, text="Save", command=self._save_image)
        self._actions_save.grid(column=2, row=1, sticky=(W, N, S))
        self._actions.columnconfigure(2, weight=1)

        self._actions_dimensions = Label(self._actions, text="???x???", anchor=CENTER)
        self._actions_dimensions.grid(column=3, row=1, sticky=(N, S))
        self._actions.columnconfigure(3, weight=1)

        self._actions_size = Label(self._actions, text="????????", anchor=E)
        self._actions_size.grid(column=4, row=1, sticky=(E, N, S))
        self._actions.columnconfigure(4, weight=1)

        # Bind
        self._source_image.bind(self._rerender_image)

        #Finally rerender
        self._rerender_image()
    def release(self):
        self._source_image.unbind(self._rerender_image)
    def parse_params(self):
        '''Parses image compression parameters from the UI and returns a dict with all the active parameters.'''
        selected_ = self._notebook.select()
        selected = self._notebook.tab(selected_)["text"]
        res = dict()
        res["Type"] = selected
        if selected == "JPEG":
            res["Quality"] = int(round(self._jpeg_slider_quality.get_value()))
            res["Subsampling"] = int(round(self._jpeg_slider_subsampling.get_value()))
        elif selected == "PNG":
            res["Compression"] = int(round(self._png_slider_compression.get_value()))
        elif selected == 'GIF':
            pass
        elif selected == 'BMP':
            pass
        elif selected == 'JPEG2000':
            pass
        else:
            raise Exception
        return res

    def _rerender_image(self):
        '''Compresses _source_image with the parameters set by the user, and replaces the _image.'''
        self._params = self.parse_params()

        if self._params["Type"] == "JPEG2000":
            return
        if self._source_image==None:
            return
        if self._source_image.image == None:
            return

        self._actions_size.configure(text="Compressing...", foreground="red")
        self._actions_size.update()

        self._image_data = compress(self._source_image.image, self._params)

        image_size = self._image_data.getbuffer().nbytes
        image_pil = PIL.Image.open(self._image_data)
        image_dimensions = image_pil.size

        self._image.replace(image_pil)

        self._actions_size.configure(text=str(image_size // 1000) + " KB", foreground="black")
        self._actions_dimensions.configure(text=str(image_dimensions[0]) + "x" + str(image_dimensions[1]))
        pass

    def _save_image(self):
        '''Save the previously compressed image to a file.'''
        filename_orig = self._source_image.name
        filename_noext = os.path.splitext(filename_orig)[0]
        ext = "." + self._params["Type"]
        path = filedialog.asksaveasfilename(defaultextension=ext,
                                            initialfile="Converted_" + filename_noext + ext)
        if path:
            with open(path, "wb") as f:
                f.write(self._image_data.getbuffer())



class ZoomableImageLabel(Frame):
    '''Like an image label, but takes a MutableImage and is zoomable by supplying a bounding box.
The underlying structure is still ttk's Label'''
    def __init__(self, image, image_controls, **kw):
        super().__init__(**kw)

        #Variables
        self._PIL_image = image
        self._tk_image = None

        self._PIL_image.bind(self.new_image)

        #UI
        self._border = 5
        self.configure(borderwidth=self._border, relief=GROOVE)

        self._label = Label(self)
        self._label.place(relx=.5, rely=.5, anchor="c")

        self._image_controls = image_controls
        self._image_controls.bind(self.new_image)

        #We delegate the drag controls to _image_controls.
        self._label.bind("<B1-Motion>", self._image_controls.drag_callback)
        self._label.bind("<Button-1>", self._image_controls.drag_callback)
        self._label.bind("<ButtonRelease-1>", self._image_controls.drag_callback)

        #Bind for size changes
        self.bind("<Configure>", self._configured)
    def release(self):
        self._image_controls.unbind(self.new_image)
        self._PIL_image.unbind(self.new_image)
    def new_image(self):
        '''Called when the _image is replaced'''
        img=self._generate_image()
        if img==None:
            #print("ZoomableImageLabel:new_image() called but image is null! Noop.")
            return
        self.tk_image = PIL.ImageTk.PhotoImage(img)
        self._label.configure(image=self.tk_image)

    def _generate_image(self):
        '''Generates a zoomed image using the _image and _image_control's viewport box.'''
        bounds = self._image_controls.get_viewport_box()
        image_bounds = self._image_controls.get_image_size()
        image_bounds_tuple = (int(round(image_bounds[0])), int(round(image_bounds[1])))
        if image_bounds[0] < (
            bounds[2] - bounds[0]) * 3:  # If the image's single pixel takes more than three pixels on the screen
            sampling = PIL.Image.CUBIC
            # print("Cubic!",image_bounds[0],bounds[2],bounds[0])
        else:
            sampling = PIL.Image.NEAREST
            # print("Nearset!")
        img = self._PIL_image.image
        if img==None:
            #print("ZoomableImageLabel:_generate_image() called but image is null! returning None.")
            return
        # print(bounds,image_bounds,image_bounds_tuple)
        return img.transform(image_bounds_tuple, PIL.Image.EXTENT, data=tuple(bounds), resample=sampling)

    def get_bounds(self):
        return (self.winfo_width(), self.winfo_height())

    def _configured(self, evt):
        '''Called when the size of the widget changes'''
        x = evt.width - self._border
        y = evt.height - self._border
        if x < 50:
            return
        if y < 50:
            return
        self._image_controls.change_window_size((x, y))


class ImageControls(Bindable):
    '''Class for controlling the ZoomableImageLabels.'''
    def __init__(self, master_image, **kwargs):
        super().__init__(**kwargs)
        self._bounding_box = [0, 0, 100, 100]  # x1 y1 x2 y2
        self._window_size = [100, 100]
        self._master_image = master_image
        master_image.bind(self._new_image)
    def release(self):
        self._master_image.unbind(self._new_image)
    def get_viewport_box(self):
        return self._bounding_box

    def get_image_size(self):
        return self._window_size

    def change_window_size(self, new_size):
        self._window_size = new_size
        # print("Window size:",new_size)
        if (self._master_image.image == None):
            return

        self._new_image()
        self._callback()

    def _window_fit_image(self):
        # Get the bounding box that entirely contains the image, using the window as its aspect ratio.
        image = self._master_image.image.size

        window_size = [self._window_size[0], self._window_size[1]]
        window_ratio = window_size[1] / window_size[0]

        image_ratio = image[1] / image[0]

        if window_ratio >= image_ratio:  # The image is longer in the X axis.
            return [0, 0, image[0], image[0] * window_ratio]
        else:  # The image is longer in the Y axis.
            return [0, 0, image[1] / window_ratio, image[1]]

    def _midpoint(self):
        return ((self._bounding_box[0] + self._bounding_box[2]) / 2,
                (self._bounding_box[1] + self._bounding_box[3]) / 2)

    def _box_size(self):
        return ((-self._bounding_box[0] + self._bounding_box[2]),
                (-self._bounding_box[1] + self._bounding_box[3]))

    def zoom(self, factor):
        midpoint = self._midpoint()
        lengths = self._box_size()
        self._bounding_box = [midpoint[0] - lengths[0] * factor / 2,
                              midpoint[1] - lengths[1] * factor / 2,
                              midpoint[0] + lengths[0] * factor / 2,
                              midpoint[1] + lengths[1] * factor / 2]

        self._callback()

    def move_scaled(self, x, y):
        # x and y is the image coordinates. We need to scale that appropriately.
        viewport_size = self._box_size()
        image_size = self._window_size
        x_scale_factor = viewport_size[0] / image_size[0]
        y_scale_factor = viewport_size[1] / image_size[1]
        # print("Scaling factors:",x_scale_factor,y_scale_factor)
        self.move_raw(x * x_scale_factor, y * y_scale_factor)

    def move_raw(self, x, y):

        self._bounding_box[0] += x
        self._bounding_box[1] += y
        self._bounding_box[2] += x
        self._bounding_box[3] += y

        self._callback()

    def scroll_callback(self, evt):
        #print(tk.focus_displayof())
        if evt.delta > 0:  # Scroll up
            self.zoom(0.8)
        else:
            self.zoom(1.2)

    def drag_callback(self, evt):
        # print("Drag Callback",evt.__dict__)
        if evt.type == '4':  # Mouse Pressed
            self._drag_start = (evt.x, evt.y)
            self._original_bounding_box = list(self._bounding_box)
        elif evt.type == '5':  # Released
            pass
        elif evt.type == '6':  # Dragged
            self._bounding_box = list(self._original_bounding_box)
            self.move_scaled(self._drag_start[0] - evt.x, self._drag_start[1] - evt.y)
            pass
        else:
            raise Exception

    def _new_image(self):
        self._bounding_box = self._window_fit_image()


class MutableImage(Bindable):
    '''A wrapper for PIL.Image that can be binded for changes.'''
    def __init__(self):
        super().__init__()
        self._image = None
        self._name = ''

    def replace(self, new_image, name="NO_NAME"):
        self._image = new_image
        self._name = name
        self._callback()

    @property
    def image(self):
        return self._image

    @property
    def name(self):
        return self._name

class BatchWindow:
    def __init__(self,master):

        self._directory_from=None
        self._directory_to=None

        self._master=master
        self._dialog=Toplevel(master)
        self._dialog.iconbitmap("32.ico")
        self._dialog.title("PICC Batch Convert")


        self._panel_directories=Frame(self._dialog)
        self._panel_directories.grid(row=1,column=1,sticky=(N,S,E,W))

        self._dialog.columnconfigure(1,weight=1)

        self._dialog.rowconfigure(2,weight=1)


        self._directories_from_button=Button(self._panel_directories,text="From",command=self._get_dir_from)
        self._directories_from_button.grid(row=1,column=1,sticky=(N,S,E,W))

        self._directories_from_label=Label(self._panel_directories,text="?")
        self._directories_from_label.grid(row=1,column=2,sticky=(N,S,E,W))
        self._panel_directories.columnconfigure(2,weight=1)

        self._directories_to_button=Button(self._panel_directories,text="to",command=self._get_dir_to)
        self._directories_to_button.grid(row=2,column=1,sticky=(N,S,E,W))

        self._directories_to_label=Label(self._panel_directories,text="?")
        self._directories_to_label.grid(row=2,column=2,sticky=(N,S,E,W))

        self._directories_start_button=Button(self._panel_directories,text="Convert!",command=self.batch_start)
        self._directories_start_button.grid(row=3,column=1,columnspan=2,sticky=(N,S,E,W))

        self._panel_results=Frame(self._dialog)
        self._panel_results.grid(row=2,column=1,sticky=(N,S,E,W))


        self._results_text=Text(self._panel_results, font=("Consolas",10), background=self._master.cget('background'))
        self._results_text.grid(row=1,column=1,sticky=(N,S,E,W))

        self._results_text.tag_config("error", foreground="red")
        self._results_text.configure(state='disabled')
        self._panel_results.columnconfigure(1,weight=1)
        self._panel_results.rowconfigure(1,weight=1)

        #scroll
        self._results_text_scroller = Scrollbar(self._panel_results, orient=VERTICAL, command=self._results_text.yview)
        self._results_text_scroller.grid(column=2, row=1, sticky=(W, E, N, S))
        self._results_text['yscrollcommand'] = self._results_text_scroller.set

        self._panel_params=Notebook(self._dialog)
        self._panel_params.grid(row=1,column=2,rowspan=2,sticky=(N,S,E,W))
        self._dialog.columnconfigure(2,weight=1)

        self._tab_code=Frame(self._panel_params)

        self._tab_code_editor=Text(self._tab_code, font=("Consolas",10))
        self._tab_code_editor.grid(row=2,column=1,sticky=(N,S,E,W))
        self._tab_code.columnconfigure(1,weight=1)
        self._tab_code.rowconfigure(2,weight=1)
        #self._tab_code_editor.insert(END,s)

        #scroll
        self._code_editor_scroller = Scrollbar(self._tab_code, orient=VERTICAL, command=self._tab_code_editor.yview)
        self._code_editor_scroller.grid(column=2, row=2, sticky=(W, E, N, S))
        self._tab_code_editor['yscrollcommand'] = self._code_editor_scroller.set

        self._tab_code_help=Button(self._tab_code,text="Help",command=self._help)
        self._tab_code_help.grid(row=1,column=1,sticky=(N,S,E,W))

        self._tab_gui=Frame(self._panel_params)

        self._tab_gui_params=ImageParameterPane(master=self._tab_gui)
        self._tab_gui_params.grid(row=1,column=1,sticky=(N,S,E,W))
        self._tab_gui.columnconfigure(1,weight=1)

        self._panel_params.add(self._tab_gui,text="GUI")
        self._panel_params.add(self._tab_code,text="Python")
    def _help(self):
        dialog=Toplevel(self._dialog)
        text=Text(dialog, font=("Consolas",10))
        text.grid(column=1,row=1,sticky=(N,S,E,W))

        dialog.columnconfigure(1,weight=1)
        dialog.rowconfigure(1,weight=1)

        #scroll
        scroller = Scrollbar(dialog, orient=VERTICAL, command=text.yview)
        scroller.grid(column=2, row=1, sticky=(W, E, N, S))
        text['yscrollcommand'] = scroller.set

        text.tag_config("heading", font=("Consolas",16), foreground="red")
        for i in s.split("\n"):
            try:
                if i[0]=='!':
                    text.insert(END,i[1:],("heading",))
                else:
                    text.insert(END,i)
            except IndexError:
                #print("IndexError")
                text.insert(END,"")
            text.insert(END,"\n")

        text.configure(state="disabled")
    def _get_dir_from(self):
        f = filedialog.askdirectory(title="Image Folder")
        if f == None or f == '':
            return
        #f=r"C:\0_User\Temp\batch"
        self._directory_from=f
        self._directories_from_label.configure(text=f)

    def _get_dir_to(self):
        f = filedialog.askdirectory(title="Image Folder")
        if f == None or f == '':
            return
        #f=r"C:\0_User\Temp\batch_dest"
        self._directory_to=f
        self._directories_to_label.configure(text=f)

    def _evaluate(self,img,filename,sizee):
        inp = self._tab_code_editor.get("1.0", 'end-1c')
        inps=inp.split("\n")
        functional='def _evaluation_function():\n'
        for i in range(len(inps)):
            functional+="    "+inps[i]+"\n"

        g={}
        g["Filename"]=filename
        g["Extension"]=os.path.splitext(filename)[-1]
        g["Filename_no_extension"]=os.path.splitext(filename)[0]
        g["Width"]=img.width
        g["Height"]=img.height
        g["Mode"]=img.mode
        g["Size"]=sizee
        exec(functional,g)
        return g["_evaluation_function"]()
    def _convert(self):
        pass
    def _close(self):
        self.dialog.destroy()
    def batch_start(self):
        selected_ = self._panel_params.select()
        tab_selected = self._panel_params.tab(selected_)["text"]


        files=os.listdir(self._directory_from)
        num=len(files)
        n=0

        for filename in files:
            n+=1
            try:
                full_path=os.path.join(self._directory_from,filename)

                img=PIL.Image.open(full_path)
                if tab_selected=="Python":
                    params=self._evaluate(img,filename,os.path.getsize(full_path))

                elif tab_selected=="GUI":
                    params=self._tab_gui_params.parse_params()
                    params["Filename"]=os.path.splitext(filename)[0]+"."+params["Type"]


                #print("Converting",full_path,"\nUsing params:",params)
                param_string="\n".join([i+" : "+str(params[i]) for i in params])

                self._results_text.configure(state='normal')
                self._results_text.insert("1.0","Converting : "+full_path+" ("+str(n)+"/"+str(num)+")"+"\n"+param_string+"\n\n")
                self._results_text.configure(state='disabled')

                self._master.update()

                if params["Type"]=="Pass":
                    continue
                if params["Type"]=="Copy":
                    with open(os.path.join(self._directory_to,params["Filename"]), "wb") as filee:
                        filee.write(open(full_path,"rb").read())
                else:
                    img_dat=compress(img,params)

                    with open(os.path.join(self._directory_to,params["Filename"]), "wb") as filee:
                        filee.write(img_dat.getbuffer())
            except:
                self._results_text.configure(state='normal')
                self._results_text.insert("1.0","Error while converting : "+full_path+"\n"+traceback.format_exc()+"\n\n",("error",))
                self._results_text.configure(state='disabled')
                break
            #sleep(1)


###Global variables###
num_images=2

mutableImage_source = MutableImage()

image_controls = ImageControls(mutableImage_source)


###Backend functions###
def new_image():
    f = filedialog.askopenfilename()
    if f == None or f == '':
        return

    global mutableimage_source
    mutableImage_source.replace(PIL.Image.open(f),
                                os.path.split(f)[1])  # Get only the file name.

    global top_open
    top_open.configure(text=f)


def batch_start():
    global tk
    BatchWindow(tk)

def compress(image, params):
    '''Compresses image into a specified format in params, and then returns a ByteIO object with the compressed data.
Params is a dict containing all the image compression parameters.'''
    output = BytesIO()

    if "Resize" in params:
        try:
            sampling={"Nearest Neighbor":PIL.Image.NEAREST,"Bilinear":PIL.Image.BILINEAR,
                      "Bicubic":PIL.Image.BICUBIC,"Lanczos":PIL.Image.LANCZOS}[params["Resize_sampling"]]
        except KeyError:
            sampling=PIL.Image.BICUBIC

        image=image.resize(params["Resize"],sampling)


    if params["Type"] == "JPEG":
        try:
            image.save(output, 'JPEG', quality=params["Quality"], subsampling=params["Subsampling"])
        except OSError:
            image.convert('RGB').save(output, 'JPEG', quality=params["Quality"], subsampling=params["Subsampling"])
    elif params["Type"] == "GIF":
        image.save(output, 'GIF')
    elif params["Type"] == "PNG":
        image.save(output, 'PNG', compress_level=params["Compression"])
    elif params["Type"] == "BMP":
        image.save(output, 'BMP')
    elif params["Type"] == "JPEG2000":
        image.save(open, "JPEG2000")
    else:
        raise Exception
    return output


###UI###

# Root
tk = Tk()
tk.title("PICC - Python Image Compression Comparer")
tk.iconbitmap("32.ico")
tk.bind_all("<MouseWheel>", image_controls.scroll_callback)

# Root>Top
top = Frame(tk)
top.grid(column=1,  row=1, padx=5, pady=5, sticky=(W, E, N, S))
tk.columnconfigure(1, weight=1)
#top.bind("<MouseWheel>", image_controls.scroll_callback)

# Root>Top>Open
top_open = Button(top, text="Open Image", command=new_image)
top_open.grid(column=1, row=1, sticky=(W, E, N, S))

# Root>Top>FilePath
top_open = Label(top, text="???")
top_open.grid(column=2, row=1, sticky=(W, E, N, S))
top.columnconfigure(2, weight=1)

# Root>Top>Batch
top_batch = Button(top, text="Batch Convert", command=batch_start)
top_batch.grid(column=3, row=1, sticky=(W, E, N, S))

# Root>Top-Image-Divider
image_top_image_divider = Separator(tk, orient=HORIZONTAL)
image_top_image_divider.grid(column=1, columnspan=3, row=2, sticky=(N, S, E, W))

#Root>Images
images_frame=Frame(tk)
images_frame.grid(column=1,  row=3,  sticky=(W, E, N, S))
images_frame.rowconfigure(1, weight=1)
tk.rowconfigure(3, weight=1)

image_panels=[]

def remove_panel():
    #print("less")
    for i in image_panels[-1]:
        #print(i)
        if hasattr(i,"release"):
            i.release()
        i.grid_forget()
        i.destroy()

    del image_panels[-1]



def more_panels(divider=True):
    panel_set=[]
    i=len(image_panels)
    new_image=MutableImage()
    #print("more",i)
    # Root>Images>Display i
    image_display = ZoomableImageLabel(new_image, image_controls, master=images_frame, height=300)
    image_display.grid(column=i*2, row=1, padx=5,pady=5, sticky=(W, E, N, S))
    #image_display.bind("<MouseWheel>", image_controls.scroll_callback)
    images_frame.rowconfigure(1, weight=1)
    images_frame.columnconfigure(i*2, weight=1)

    # Root>Images>Params i
    image_params = ImageParameterPane(new_image, mutableImage_source, master=images_frame, height=300)
    image_params.grid(column=i*2, row=2, padx=5,pady=5,sticky=(W, E, N, S))

    if divider:
        # Root>Images>Divider i
        image_divider = Separator(images_frame, orient=VERTICAL)
        image_divider.grid(column=i*2+1, row=1,rowspan=2, sticky=(N, S, E, W))
        panel_set.append(image_divider)

    panel_set.append(image_display)
    panel_set.append(image_params)

    image_panels.append(panel_set)

for i in range(num_images):
   more_panels()

buttons=Frame(images_frame)
buttons.grid(column=100, row=2, padx=5,pady=5,sticky=(W, E, N, S))

more_btn=Button(buttons,text="+",command=more_panels)
more_btn.grid(column=1, row=1, padx=5,pady=5,sticky=(W, E, N, S))
buttons.rowconfigure(1,weight=1)

less_btn=Button(buttons,text="-",command=remove_panel)
less_btn.grid(column=1, row=2, padx=5,pady=5,sticky=(W, E, N, S))
buttons.rowconfigure(2,weight=1)

tk.mainloop()
