# $1 is a .class file like #my/UnsignedByteToFloatSamplerConverter.class
java -classpath /home/albert/Programming/fiji-new/Fiji.app/jars/imglib2-5.1.0.jar:/home/albert/Programming/fiji-new/Fiji.app/jars/asm-5.0.4.jar://home/albert/Programming/fiji-new/Fiji.app/jars/asm-util-5.0.4.jar org.objectweb.asm.util.ASMifier $1
