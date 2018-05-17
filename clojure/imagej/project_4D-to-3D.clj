(use '[clojure.java.io])
(import [ij IJ ImageStack]
        [ij.process ImageProcessor]
        [ij.io DirectoryChooser])

;(set! *unchecked-math* true)
;(set! *warn-on-reflection* true)

; TEST
;(def srcDir "/home/albert/Desktop/test-stacks/")
;(def stack-file-pattern #".*\.tif") ;#".*CM00_CHN01\.klb") ; #".*\.tif"

; WARNING: remember to enable ImageJ SCIFIO to be able to load .klb files, under "Edit - Options - ImageJ2..."

(def srcDir "/home/albert/shares/zlaticlab/Nadine/Raghav/2017-05-10/GCaMP6s_1_20170510_115003.corrected/dff_on_fused/from_Raghav/MVD_Results/")
(def stack-file-pattern #".*CM00_CHN00\.klb")

; Compute pixel-wise max for a pair of ImagePlus
; storing the result into the first one.
; Will flush the second ImagePlus.
(defn maxer [max_imp imp]
  (let [#^ImageStack stack1 (.getStack max_imp)
        #^ImageStack stack2 (.getStack imp)
        #^int length (* (.getWidth max_imp) (.getHeight max_imp))]
    (println "Processing:" (.getTitle imp))
    ; for every slice, do pixel-wise max
    (doseq [slice (range 1 (inc (.getSize stack1)))]
      (let [#^ImageProcessor ip1 (.getProcessor stack1 slice)
            #^ImageProcessor ip2 (.getProcessor stack2 slice)]
        (loop [i 0]
          (when (< i length)
            (.setf ip1 i (max (.getf ip1 i) (.getf ip2 i)))
            (recur (inc i))))))
    ; release memory
    (.flush imp)
    ; return max projection
    max_imp))

; Return a lazy iterator over all files under the folder at dirpath
; whose names match the regex pattern.
(defn filter-walk [dirpath pattern]
  (doall (filter #(re-matches pattern (.getName %))
                 (file-seq (file dirpath)))))

(defn exec [folder]
  (doto (reduce maxer
                (map #(IJ/openImage (.getPath %))
                     (filter-walk folder stack-file-pattern)))
    (.setTitle "max projection")
    (.show)))

; Folder chooser
;(let [dc (DirectoryChooser. "Use folder")
;      folder (.getDirectory dc)]
;  (if folder
;    (exec folder)
;    (println "User cancelled.")))

(exec srcDir)