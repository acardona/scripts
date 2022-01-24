(ns my.ij3d.segmentator
  (:import [ij3d Image3DUniverse]
           [java.awt.event MouseAdapter MouseEvent]))

(def univ (Image3DUniverse. 512 512))
(.show univ)

; An agent to run the segmentations in a separate thread:
(def segmentator (agent nil))

(.. univ getCanvas (addMouseListener
  (proxy [MouseAdapter] []
    (mousePressed [event]
      (send segmentator (fn [_] (report event)))))))


(defn report [#^MouseEvent event]
  (let [picker (.. univ getPicker)
        content (.getPickedContent picker (.getX event) (.getY event))]
    (when content
      (println content)
      (let [point (.getPickPointGeometry picker content (.getX event) (.getY event))
            imp (.getImage content)]
        (when imp
          (let [copy (.run (ij.plugin.Duplicator.) imp)
                calibration (.getCalibration copy)]
             (.show copy)
             (println point)
             ; Scroll to the clicked point in the stack
             (.setSlice copy (inc (/ (.z point) (.pixelDepth calibration))))
             (let [proi (ij.gui.PointRoi. (int (/ (.x point) (.pixelWidth calibration)))
                                          (int (/ (.y point) (.pixelHeight calibration))))]
               (.setRoi copy proi)
               (when-let [seg (.execute (levelsets.ij.LevelSet.) copy false)]
                 ;(let [triangles (.getTriangles (marchingcubes.MCTriangulator.) seg 1 (into-array Boolean/TYPE (repeat 3 true)) 4)])
                 (ij.IJ/run seg "Invert" "")
                 (.addContent univ seg (javax.vecmath.Color3f. java.awt.Color/red) "Mesh" 1 (into-array Boolean/TYPE (repeat 3 true)) 4 ij3d.Content/SURFACE)))
             ))))))
