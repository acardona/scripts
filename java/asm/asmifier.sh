# $1 is a .class file like #my/UnsignedByteToFloatSamplerConverter.class
java -classpath /home/albert/software/Fiji.app/jars/imglib2-5.12.0.jar:/home/albert/software/Fiji.app/jars/asm-7.1.jar://home/albert/software/Fiji.app/jars/asm-util-7.1.jar org.objectweb.asm.util.ASMifier $1
