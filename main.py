###Imports###
#PIL and tkinter has conflicting names, so we do this.
import PIL.Image
import PIL.ImageTk
import PIL.ImageOps

from tkinter import *
from tkinter.ttk import *
from tkinter import filedialog

from io import BytesIO
from time import time
import os
import webbrowser


###Classes###
#Base class for classes implementing an Observer pattern.
class Bindable:
    def __init__(self, **kwargs):
        #pass
        self._callbacks=list()
        super().__init__(**kwargs)
    def bind(self,callbcak):
        self._callbacks.append(callbcak)
    def _callback(self):
        for i in self._callbacks:
            i()

#Slider with a label and a value display.
#expects these keyword argumemts:
#plus_name, plus_max,plus_min,plus_divisions,plus_format,plus_callback
class SliderPlus(Bindable,Frame):
    def __init__(self, **kw):
        #Variables
        self._plus_name=kw["plus_name"]
        self._plus_max=kw["plus_max"]
        self._plus_min=kw["plus_min"]
        self._plus_divisions=kw["plus_divisions"]
        self._plus_format=kw["plus_format"]
        self._plus_callback=kw["plus_callback"]

        self._plus_value=self._plus_min

        #This is ugly.(duh)
        del kw["plus_name"]
        del kw["plus_max"]
        del kw["plus_min"]
        del kw["plus_divisions"]
        del kw["plus_format"]
        del kw["plus_callback"]

        super().__init__(**kw)

        # Label
        self._plus_label=Label(self,text=self._plus_name)
        self._plus_label.grid(row=1,column=1)

        #Slider
        self._plus_slider = Scale(self, orient=HORIZONTAL, length=200, from_=0, to=self._plus_divisions,value=0,
                                          command=self._plus_slider_changed)
        self._plus_slider.grid(column=2, row=1, sticky=(W, E))
        self.columnconfigure(2,weight=1)

        self._plus_slider.bind("<ButtonRelease>",self._slider_released)

        # Value

        self._plus_value_str_label = Label(self, text=str(self._plus_min))
        self._plus_value_str_label.grid(column=3, row=1, sticky=(W, E))

    def _slider_released(self,evt):
        self._callback()
    def _plus_slider_changed(self,x):
        self._plus_value=int(round(float(x)))/self._plus_divisions*(self._plus_max-self._plus_min)+self._plus_min
        self._plus_value_str_label.configure(text=("{:."+str(self._plus_format)+"f}").format(self._plus_value))
    def get_value(self):
        return self._plus_value


#This class generates an image parameter pane, containing all the parameters for the iamge compression.
#After parameters are changed, it compresses a source_image and replaces image
class ImageParameterPane(Frame):
    def __init__(self, image, source_image, **kw):

        super().__init__(**kw)
        self._image=image
        self._source_image=source_image

        self._params=None
        self._image_data=None

        #UI
        self._notebook=Notebook(self)
        self._notebook.grid(column=1, row=1, sticky=(W, E, N, S))
        self._notebook.bind("<ButtonRelease>",lambda e: self._rerender_image())
        self.columnconfigure(1,weight=1)

        self._tab_png=Frame(self)
        self._png_slider_compression=SliderPlus(plus_name="Compression",plus_divisions=9,plus_format=0,
                                             plus_min=0,plus_max=9,plus_callback=None,master=self._tab_png)
        self._png_slider_compression.grid(column=1, row=1, sticky=(W, E, N, S))
        self._png_slider_compression.bind(self._rerender_image)

        self._tab_jpeg=Frame(self)
        self._jpeg_slider_quality=SliderPlus(plus_name="Quality",plus_divisions=99,plus_format=0,
                                             plus_min=1,plus_max=100,plus_callback=None,master=self._tab_jpeg)
        self._jpeg_slider_quality.grid(column=1, row=1, sticky=(W, E, N, S))
        self._jpeg_slider_quality.bind(self._rerender_image)

        self._jpeg_slider_subsampling=SliderPlus(plus_name="Chroma Subsampling",plus_divisions=2,plus_format=0,
                                      plus_min=0,plus_max=2,plus_callback=None,master=self._tab_jpeg)
        self._jpeg_slider_subsampling.grid(column=1, row=2, sticky=(W, E, N, S))
        self._jpeg_slider_subsampling.bind(self._rerender_image)

        self._tab_gif=Frame(self)
        self._gif_label=Label(self._tab_gif,text="No Options.")
        self._gif_label.grid(column=1, row=1, sticky=(W, E, N, S))
        self._tab_gif.columnconfigure(1,weight=1)

        self._tab_bmp=Frame(self)
        self._bmp_label=Label(self._tab_bmp,text="No Options.")
        self._bmp_label.grid(column=1, row=1, sticky=(W, E, N, S))
        self._tab_bmp.columnconfigure(1,weight=1)


        self._tab_jpeg2=Frame(self)
        self._jpeg2_label=Label(self._tab_jpeg2,text="Well...(Click here)", foreground="blue", cursor="hand2")
        self._jpeg2_label.bind("<Button-1>", lambda e: webbrowser.open_new(r"https://github.com/python-pillow/Pillow/issues/1945"))
        self._jpeg2_label.grid(column=1, row=1, sticky=(W, E, N, S))

        self._notebook.add(self._tab_png,text="PNG")
        self._notebook.add(self._tab_gif,text="GIF")
        self._notebook.add(self._tab_jpeg,text="JPEG")
        self._notebook.add(self._tab_bmp,text="BMP")
        self._notebook.add(self._tab_jpeg2,text="JPEG2000")

        self._actions=Frame(self)
        self._actions.grid(column=1, row=2, sticky=(W, E, N, S))


        #self._actions_compress=Button(self._actions,text="Compress",command=self._rerender_image)
        #self._actions_compress.grid(column=1, row=1, sticky=(W, E, N, S))

        self._actions_save=Button(self._actions,text="Save",command=self._save_image)
        self._actions_save.grid(column=2, row=1, sticky=(W, N, S))
        self._actions.columnconfigure(2,weight=1)

        self._actions_dimensions=Label(self._actions,text="???x???",anchor=CENTER)
        self._actions_dimensions.grid(column=3, row=1, sticky=(N, S))
        self._actions.columnconfigure(3,weight=1)

        self._actions_size=Label(self._actions,text="????????",anchor=E)
        self._actions_size.grid(column=4, row=1, sticky=(E, N, S))
        self._actions.columnconfigure(4,weight=1)

        #Bind

        self._source_image.bind(self._rerender_image)

    def _parse_params(self):
        selected_=self._notebook.select()
        selected=self._notebook.tab(selected_)["text"]
        res=dict()
        res["Type"]=selected
        if selected=="JPEG":
            res["Quality"]=int(self._jpeg_slider_quality.get_value())
            res["Subsampling"]=int(self._jpeg_slider_subsampling.get_value())
        elif selected=="PNG":
            res["Compression"]=int(self._png_slider_compression.get_value())
        elif selected=='GIF':
            pass
        elif selected=='BMP':
            pass
        elif selected=='JPEG2000':
            pass
        else:
            raise Exception
        #print(res)
        return res
    def _rerender_image(self):
        self._params=self._parse_params()

        if self._params["Type"]=="JPEG2000":
            return
        if self._source_image.image==None:
            return

        self._actions_size.configure(text="Compressing...",foreground="red")
        self._actions_size.update()


        self._image_data=compress(self._source_image.image,self._params)

        image_size=self._image_data.getbuffer().nbytes
        image_pil=PIL.Image.open(self._image_data)
        image_dimensions=image_pil.size

        self._image.replace(image_pil)

        self._actions_size.configure(text=str(image_size//1000)+" KB",foreground="black")
        self._actions_dimensions.configure(text=str(image_dimensions[0])+"x"+str(image_dimensions[1]))
        pass
    def _save_image(self):
        filename_orig=self._source_image.name
        filename_noext=os.path.splitext(filename_orig)[0]
        ext="."+self._params["Type"]
        path=filedialog.asksaveasfilename(defaultextension=ext,
                                          initialfile="Converted_"+filename_noext+ext)
        if path:
            with open(path,"wb") as f:
                f.write(self._image_data.getbuffer())


#Like an image label, but takes a MutableImage.Image and is zoomable.
#Underlying structure is still tk's Label
class ZoomableImageLabel(Frame):
    def __init__(self, image, image_controls, **kw):
        super().__init__(**kw)

        self._PIL_image=image

        self._tk_image=None


        self._PIL_image.bind(self.new_image)

        self._border=5
        self.configure(borderwidth=self._border,relief=GROOVE)

        self._label=Label(self)
        self._label.place(relx=.5, rely=.5, anchor="c")
        #self._label.grid(row=1,column=1)

        self._image_controls=image_controls
        self._image_controls.bind(self.new_image)

        self._label.bind("<B1-Motion>",self._image_controls.drag_callback)
        self._label.bind("<Button-1>",self._image_controls.drag_callback)
        self._label.bind("<ButtonRelease-1>",self._image_controls.drag_callback)

        self.bind("<Configure>",self._configured)
    def new_image(self):
        self.tk_image=PIL.ImageTk.PhotoImage(self._generate_image())
        self._label.configure(image=self.tk_image)

    def _generate_image(self):
        bounds=self._image_controls.get_viewport_box()
        image_bounds=self._image_controls.get_image_size()
        image_bounds_tuple=(int(round(image_bounds[0])),int(round(image_bounds[1])))
        if image_bounds[0]<(bounds[2]-bounds[0])*3: #If the image's single pixel takes more than three pixels on the screen
            sampling=PIL.Image.CUBIC
            #print("Cubic!",image_bounds[0],bounds[2],bounds[0])
        else:
            sampling=PIL.Image.NEAREST
            #print("Nearset!")
        img=self._PIL_image.image
        #print(bounds,image_bounds,image_bounds_tuple)
        return img.transform(image_bounds_tuple,PIL.Image.EXTENT,data=tuple(bounds),resample=sampling)
    def get_bounds(self):
        return (self.winfo_width(),self.winfo_height())
    def _configured(self,evt):
        x=evt.width-self._border
        y=evt.height-self._border
        if x<50:
            return
        if y<50:
            return
        self._image_controls.change_window_size((x,y))

class ImageControls(Bindable):
    def __init__(self,master_image, **kwargs):
        super().__init__(**kwargs)
        self._bounding_box=[0,0,100,100] #x1 y1 x2 y2
        self._window_size=[100,100]
        self._master_image=master_image
        master_image.bind(self._new_image)
    def get_viewport_box(self):
        return self._bounding_box
    def get_image_size(self):
        return self._window_size
    def change_window_size(self,new_size):
        self._window_size=new_size
        #print("Window size:",new_size)
        if (self._master_image.image==None):
            return

        self._new_image()
        self._callback()

    def _window_fit_image(self):
        #Get the bounding box that entirely contains the image, using the window as its aspect ratio.
        image=self._master_image.image.size

        window_size=[self._window_size[0],self._window_size[1]]
        window_ratio=window_size[1]/window_size[0]

        image_ratio=image[1]/image[0]

        if window_ratio>=image_ratio: # The image is longer in the X axis.
            return [0,0,image[0],image[0]*window_ratio]
        else: # The image is longer in the Y axis.
            return [0,0,image[1]/window_ratio,image[1]]
    def _midpoint(self):
        return ((self._bounding_box[0]+self._bounding_box[2])/2,
                  (self._bounding_box[1]+self._bounding_box[3])/2)
    def _box_size(self):
        return ((-self._bounding_box[0]+self._bounding_box[2]),
                  (-self._bounding_box[1]+self._bounding_box[3]))
    def zoom(self, factor):
        midpoint=self._midpoint()
        lengths=self._box_size()
        self._bounding_box= [midpoint[0]-lengths[0]*factor/2,
                             midpoint[1]-lengths[1]*factor/2,
                             midpoint[0]+lengths[0]*factor/2,
                             midpoint[1]+lengths[1]*factor/2]


        self._callback()
    def move_scaled(self,x,y):
        #x and y is the image coordinates. We need to scale that appropriately.
        viewport_size=self._box_size()
        image_size=self._window_size
        x_scale_factor=viewport_size[0]/image_size[0]
        y_scale_factor=viewport_size[1]/image_size[1]
        #print("Scaling factors:",x_scale_factor,y_scale_factor)
        self.move_raw(x*x_scale_factor,y*y_scale_factor)
    def move_raw(self,x,y):

        self._bounding_box[0]+=x
        self._bounding_box[1]+=y
        self._bounding_box[2]+=x
        self._bounding_box[3]+=y

        self._callback()
    def scroll_callback(self,evt):
        if evt.delta>0: #Scroll up
            self.zoom(0.8)
        else:
            self.zoom(1.2)
    def drag_callback(self,evt):
        #print("Drag Callback",evt.__dict__)
        if evt.type=='4': #Mouse Pressed
            self._drag_start=(evt.x,evt.y)
            self._original_bounding_box=list(self._bounding_box)
        elif evt.type=='5': #Released

            pass
        elif evt.type=='6': #Dragged
            self._bounding_box=list(self._original_bounding_box)
            self.move_scaled(self._drag_start[0]-evt.x,self._drag_start[1]-evt.y)
            pass
        else:
            raise Exception

    def _new_image(self):
        self._bounding_box=self._window_fit_image()



class MutableImage(Bindable):
    def __init__(self):
        super().__init__()
        self._image=None
        self._name=''
    def replace(self,new_image,name="NO_NAME"):
        self._image=new_image
        self._name=name
        self._callback()
    @property
    def image(self):
        return self._image
    @property
    def name(self):
        return self._name


###Global variables###
mutableImage_source=MutableImage()
mutableImage_A=MutableImage()
mutableImage_B=MutableImage()
image_controls=ImageControls(mutableImage_source)

###Backend functions###
def new_image():
    f=filedialog.askopenfilename()
    if f==None or f=='':
        return

    global mutableimage_source
    mutableImage_source.replace(PIL.Image.open(f),
                                os.path.split(f)[1]) #Get only the file name.

    global top_open
    top_open.configure(text=f)




#Compresses image into a specified format in params, and then returns a ByteIO object with the compressed data.
#Params is a dict containing all the image compression parameters.
#  Params["Type"] = "JPEG" / "GIF" / "PNG"
#    if JPEG, required elements are "Quality" and "Subsampling"
def compress(image, params):
    output = BytesIO()
    if params["Type"]=="JPEG":
        image.save(output, 'JPEG', quality=params["Quality"], subsampling=params["Subsampling"])
    elif params["Type"]=="GIF":
        image.save(output,'GIF')
    elif params["Type"]=="PNG":
        image.save(output,'PNG',compress_level=params["Compression"])
    elif params["Type"]=="BMP":
        image.save(output,'BMP')
    elif params["Type"]=="JPEG2000":
        image.save(open,"JPEG2000")
    else:
        raise Exception
    return output

###UI###

#Root
tk=Tk()
tk.title("PICC - Pyton Image Compression Comparer")
tk.iconbitmap("32.ico")
tk.bind_all("<MouseWheel>",image_controls.scroll_callback)


#Root>Top
top=Frame(tk)
top.grid(column=1, columnspan=3, row=1,padx=5,pady=5,  sticky=(W, E, N, S))
tk.columnconfigure(1, weight=1)

#Root>Top>Open
top_open=Button(top,text="Open Image",command=new_image)
top_open.grid(column=1, row=1, sticky=(W, E, N, S))

#Root>Top>FilePath
top_open=Label(top,text="???")
top_open.grid(column=2, row=1, sticky=(W, E, N, S))
top.columnconfigure(2, weight=1)


#Root>Top-Image-Divider
image_top_image_divider=Separator(tk,orient=HORIZONTAL)
image_top_image_divider.grid(column=1,columnspan=3,row=2,sticky=(N,S,E,W))

#Root>ImageA
image_A=Frame(tk)
image_A.grid(column=1, row=3,padx=5,pady=5,  sticky=(W, E, N, S))
tk.rowconfigure(3, weight=1)
tk.columnconfigure(1, weight=1)

#Root>ImageA>ImageADisplay
image_A_display=ZoomableImageLabel(mutableImage_A,image_controls,master=image_A,height=300)
image_A_display.grid(column=1, row=1, sticky=(W, E, N, S))
image_A.rowconfigure(1, weight=1)
image_A.columnconfigure(1, weight=1)

#Root>ImageA>ImageAParams
image_A_params=ImageParameterPane(mutableImage_A,mutableImage_source,master=image_A,height=300)
image_A_params.grid(column=1, row=2, sticky=(W, E, N, S))

#Root>AB-Divider
image_AB_divider=Separator(tk,orient=VERTICAL)
image_AB_divider.grid(column=2,row=3,sticky=(N,S,E,W))


#Root>ImageB
image_B=Frame(tk)
image_B.grid(column=3, row=3,padx=5,pady=5,  sticky=(W, E, N, S))
tk.columnconfigure(3, weight=1)

#Root>ImageB>ImageBDisplay
image_B_display=ZoomableImageLabel(mutableImage_B,image_controls,master=image_B)
image_B_display.grid(column=1, row=1, sticky=(W, E, N, S))
image_B.rowconfigure(1, weight=1)
image_B.columnconfigure(1, weight=1)

#Root>ImageB>ImageBParams
image_B_params=ImageParameterPane(mutableImage_B,mutableImage_source,master=image_B)
image_B_params.grid(column=1, row=2, sticky=(W, E, N, S))



'''
img=PIL.Image.open(r"C:\0_User\Temp\to phone\rainbow_by_fajeh-d5b0w60.png")



#contents = output.getvalue()
#output.close()
print(output.getbuffer().nbytes)



img2=PIL.Image.open(output)
img3=img2.transform(img2.size,PIL.Image.EXTENT,data=(0, 0, img2.size[0]//3, img2.size[1]//3),resample=PIL.Image.NEAREST)

pi=PIL.ImageTk.PhotoImage(image=img3)

lb=Label(image=pi)
lb.image=pi # We do this so the image won't get GC'd.
lb.pack()
'''
tk.mainloop()
