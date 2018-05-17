(use '[clojure.java.io])
(import [org.janelia.simview.klb KLB]
        [net.imagej ImgPlus]
        [net.imglib2 Cursor]
        [net.imglib2.type.numeric.integer UnsignedShortType]
        [net.imglib2.img.display.imagej ImageJFunctions]
        [ij.io DirectoryChooser])

;(set! *unchecked-math* true)
;(set! *warn-on-reflection* true)

; TEST
;(def srcDir "/home/albert/Desktop/test-stacks/")
;(def stack-file-pattern #".*\.tif") ;#".*CM00_CHN01\.klb") ; #".*\.tif"

(def srcDir "/home/albert/shares/zlaticlab/Nadine/Raghav/2017-05-10/GCaMP6s_1_20170510_115003.corrected/dff_on_fused/from_Raghav/MVD_Results/")
(def stack-file-pattern #".*CM00_CHN00\.klb")

; Define sublist from index 10 to index 14 would be: 10 - 15
(def start-index 10)
(def end-index 15)

;; DON't EDIT BEYOND HERE

(def klb (KLB/newInstance))

; Compute pixel-wise max for a pair of ImgPlus
; storing the result into the first one.
(defn maxer [^ImgPlus max_img
             ^ImgPlus img]
  (let [^Cursor c1 (.cursor max_img)
        ^Cursor c2 (.cursor img)]
    (loop []
      (when (.hasNext c1)
        (.next c1)
        (.next c2)
        (let [^UnsignedShortType s1 (.get c1)
              ^UnsignedShortType s2 (.get c2)]
          (.set s1 (short (max (.get s1) (.get s2))))
          (recur)))))
  max_img)

; Return a lazy iterator over all files under the folder at dirpath
; whose names match the regex pattern.
(defn filter-walk [dirpath pattern]
  (doall (filter #(re-matches pattern (.getName %))
                 (file-seq (file dirpath)))))

(defn sublist [folder]
  (subvec 
    (vec (sort (filter-walk folder stack-file-pattern)))
    start-index
    end-index))

(defn exec [folder]
  (let [img (reduce maxer
                    (map #(let [path (.getPath %)
                                img (.readFull klb path)]
                            (println path)
                            img)
                         (sublist folder)))
        imp (ImageJFunctions/wrap img "max projection")]
    (.show imp)))

; Folder chooser
;(let [dc (DirectoryChooser. "Use folder")
;      folder (.getDirectory dc)]
;  (if folder
;    (exec folder)
;    (println "User cancelled.")))

(exec srcDir)
